import yfinance as yf
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from stocks.models import Stock
from django.core.cache import cache
from datetime import datetime, timedelta
import logging
import asyncio
import concurrent.futures
from .rate_limiter import stock_rate_limiter, retry_with_backoff

logger = logging.getLogger(__name__)

@retry_with_backoff(max_retries=3, initial_delay=2, max_delay=30)
def get_stock_info(symbol):
    """Helper function to fetch stock info with caching and rate limiting"""
    cache_key = f'stock_info_{symbol}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        # Check if cache is still fresh (less than 5 minutes old)
        if (datetime.now() - cached_data['timestamp']).seconds < 300:
            return cached_data['data']
    
    # Check rate limit before making API call
    if stock_rate_limiter.is_rate_limited(symbol):
        raise Exception('Too Many Requests')
        
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        if info and 'symbol' in info:
            cache_data = {
                'timestamp': datetime.now(),
                'data': info
            }
            cache.set(cache_key, cache_data, timeout=600)  # Cache for 10 minutes max
            return info
    except Exception as e:
        logger.error(f"Error fetching stock info for {symbol}: {str(e)}")
        raise e

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_stocks(request):
    try:
        query = request.GET.get('q', '').strip().upper()
        if len(query) < 2:
            return Response([], status=status.HTTP_200_OK)

        # Search for stocks using yfinance
        matching_stocks = []
        try:
            # Try exact symbol match first
            info = get_stock_info(query)
            if info:
                matching_stocks.append({
                    'symbol': info['symbol'],
                    'name': info.get('longName', info.get('shortName', '')),
                    'exchange': info.get('exchange', ''),
                    'current_price': info.get('regularMarketPrice', 0),
                    'change': info.get('regularMarketChange', 0),
                    'change_percent': info.get('regularMarketChangePercent', 0)
                })
        except Exception as e:
            logger.warning(f"Error fetching exact stock match for {query}: {str(e)}")

        # If no exact match or error, try search
        if not matching_stocks:
            # This is a mock implementation since yfinance doesn't provide direct search
            # In production, you might want to use a proper market data API
            common_stocks = {
                'AAPL': 'Apple Inc.',
                'MSFT': 'Microsoft Corporation',
                'GOOGL': 'Alphabet Inc.',
                'AMZN': 'Amazon.com Inc.',
                'META': 'Meta Platforms Inc.',
                'TSLA': 'Tesla Inc.',
                'NVDA': 'NVIDIA Corporation',
                'JPM': 'JPMorgan Chase & Co.',
                'BAC': 'Bank of America Corp.',
                'WMT': 'Walmart Inc.'
            }

            for symbol, name in common_stocks.items():
                if query in symbol or query.lower() in name.lower():
                    try:
                        info = get_stock_info(symbol)
                        if info:
                            matching_stocks.append({
                            'symbol': symbol,
                            'name': name,
                            'exchange': info.get('exchange', ''),
                            'current_price': info.get('regularMarketPrice', 0),
                            'change': info.get('regularMarketChange', 0),
                            'change_percent': info.get('regularMarketChangePercent', 0)
                        })
                    except Exception as e:
                        logger.warning(f"Error fetching stock data for {symbol}: {str(e)}")
                        continue

        return Response(matching_stocks[:5], status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in stock search: {str(e)}")
        return Response({'error': 'An error occurred while searching for stocks'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

async def fetch_stock_data(symbol):
    """Asynchronously fetch stock data"""
    try:
        info = get_stock_info(symbol)
        if not info or 'symbol' not in info:
            return None, None

        # Use ThreadPoolExecutor for CPU-bound operations
        with concurrent.futures.ThreadPoolExecutor() as executor:
            stock = yf.Ticker(symbol)
            future = executor.submit(lambda: stock.history(period='1y'))
            hist = future.result(timeout=10)  # 10 seconds timeout

        historical_data = {
            'dates': hist.index.strftime('%Y-%m-%d').tolist(),
            'prices': hist['Close'].tolist(),
            'volumes': hist['Volume'].tolist()
        }
        
        return info, historical_data
    except Exception as e:
        logger.error(f"Error in fetch_stock_data for {symbol}: {str(e)}")
        return None, None

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stock_data(request, symbol):
    try:
        # Run async function in sync context
        info, historical_data = asyncio.run(fetch_stock_data(symbol))
        
        if not info or not historical_data:
            return Response({'error': 'Stock not found or data unavailable'}, 
                           status=status.HTTP_404_NOT_FOUND)

        response_data = {
            'symbol': info['symbol'],
            'name': info.get('longName', info.get('shortName', '')),
            'exchange': info.get('exchange', ''),
            'current_price': info.get('regularMarketPrice', 0),
            'change': info.get('regularMarketChange', 0),
            'change_percent': info.get('regularMarketChangePercent', 0),
            'market_cap': info.get('marketCap', 0),
            'volume': info.get('regularMarketVolume', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'eps': info.get('trailingEps', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'historical_data': historical_data
        }

        # Update or create stock in database
        stock_obj, created = Stock.objects.update_or_create(
            symbol=info['symbol'],
            defaults={
                'name': info.get('longName', info.get('shortName', '')),
                'current_price': info.get('regularMarketPrice', 0),
                'previous_close': info.get('regularMarketPreviousClose', 0),
                'change': info.get('regularMarketChange', 0),
                'change_percent': info.get('regularMarketChangePercent', 0)
            }
        )

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error fetching stock data for {symbol}: {str(e)}")
        return Response({'error': 'An error occurred while fetching stock data'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)