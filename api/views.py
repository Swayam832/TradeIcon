from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .angel_api import AngelBrokingAPI
from .strategy import enhanced_pullback_strategy
from .prediction import predict_stock_price
from stocks.models import Stock, Watchlist, Portfolio, StockPrediction, TradeSignal, StockNews
import pandas as pd
import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
import yfinance as yf
from newsapi import NewsApiClient

class StockDataAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, symbol):
        try:
            # Get real-time data from Yahoo Finance
            stock_data = yf.Ticker(symbol)
            if not stock_data:
                return Response({'error': 'Invalid stock symbol'}, status=status.HTTP_404_NOT_FOUND)
            
            # Get historical data
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=365)
            df = stock_data.history(start=start_date, end=end_date, interval='1d')
            if df.empty:
                return Response({'error': 'No historical data available'}, status=status.HTTP_404_NOT_FOUND)
            
            # Get real-time quote
            quote = stock_data.info
            current_price = quote.get('regularMarketPrice', 0)
            prev_close = quote.get('previousClose', 0)
            change = current_price - prev_close if current_price and prev_close else 0
            change_percent = (change / prev_close * 100) if change and prev_close else 0
            
            # Update stock in database
            stock, created = Stock.objects.update_or_create(
                symbol=symbol,
                defaults={
                    'name': quote.get('longName', f"{symbol} Company"),
                    'current_price': current_price,
                    'previous_close': prev_close,
                    'change': change,
                    'change_percent': change_percent
                }
            )
            
            # Get latest news
            try:
                newsapi = NewsApiClient(api_key='your-news-api-key')
                news = newsapi.get_everything(
                    q=f"{symbol} OR {quote.get('longName', '')}",
                    language='en',
                    sort_by='publishedAt',
                    page_size=5
                )
            except Exception as e:
                news = {'articles': []}
                logger.error(f"Error fetching news for {symbol}: {str(e)}")
            
            # Save news to database
            for article in news.get('articles', []):
                StockNews.objects.create(
                    stock=stock,
                    title=article['title'],
                    content=article['description'],
                    url=article['url'],
                    source=article['source']['name'],
                    published_at=article['publishedAt']
                )
            
            return Response({
                'symbol': symbol,
                'name': stock.name,
                'current_price': float(stock.current_price) if stock.current_price else None,
                'change': float(stock.change) if stock.change else None,
                'change_percent': float(stock.change_percent) if stock.change_percent else None,
                'historical_data': {
                    'dates': df.index.strftime('%Y-%m-%d').tolist(),
                    'open': df['Open'].tolist(),
                    'high': df['High'].tolist(),
                    'low': df['Low'].tolist(),
                    'close': df['Close'].tolist(),
                    'volume': df['Volume'].tolist()
                },
                'company_info': {
                    'sector': quote.get('sector'),
                    'industry': quote.get('industry'),
                    'market_cap': quote.get('marketCap'),
                    'pe_ratio': quote.get('trailingPE'),
                    'dividend_yield': quote.get('dividendYield')
                }
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get current price (mock)
        current_price = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100
        
        # Update stock in database
        stock, created = Stock.objects.update_or_create(
            symbol=symbol,
            defaults={
                'name': f"{symbol} Company",
                'current_price': current_price,
                'change': change,
                'change_percent': change_percent
            }
        )
        
        return Response({
            'symbol': symbol,
            'name': stock.name,
            'current_price': float(stock.current_price),
            'change': float(stock.change),
            'change_percent': float(stock.change_percent),
            'historical_data': {
                'dates': df.index.strftime('%Y-%m-%d').tolist(),
                'open': df['open'].tolist(),
                'high': df['high'].tolist(),
                'low': df['low'].tolist(),
                'close': df['close'].tolist(),
                'volume': df['volume'].tolist()
            }
        })

class StrategyAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, symbol):
        # Get historical data (mock data for demonstration)
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=365)
        
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        data = {
            'open': [100 + i * 0.1 + (i % 10) for i in range(len(dates))],
            'high': [105 + i * 0.1 + (i % 10) for i in range(len(dates))],
            'low': [95 + i * 0.1 + (i % 10) for i in range(len(dates))],
            'close': [102 + i * 0.1 + (i % 10) for i in range(len(dates))],
            'volume': [1000000 + i * 1000 for i in range(len(dates))]
        }
        df = pd.DataFrame(data, index=dates)
        
        # Apply strategy
        long_ma = int(request.query_params.get('long_ma', 50))
        short_ma = int(request.query_params.get('short_ma', 20))
        stop_loss_pct = float(request.query_params.get('stop_loss_pct', 0.02))
        
        strategy_results = enhanced_pullback_strategy(df, long_ma, short_ma, stop_loss_pct)
        
        return Response(strategy_results)

class PredictionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, symbol):
        # Get historical data (mock data for demonstration)
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=365)
        
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        data = {
            'open': [100 + i * 0.1 + (i % 10) for i in range(len(dates))],
            'high': [105 + i * 0.1 + (i % 10) for i in range(len(dates))],
            'low': [95 + i * 0.1 + (i % 10) for i in range(len(dates))],
            'close': [102 + i * 0.1 + (i % 10) for i in range(len(dates))],
            'volume': [1000000 + i * 1000 for i in range(len(dates))]
        }
        df = pd.DataFrame(data, index=dates)
        
        # Make predictions
        days_ahead = int(request.query_params.get('days_ahead', 5))
        prediction_results = predict_stock_price(df, days_ahead)
        
        # Store predictions in database
        stock = get_object_or_404(Stock, symbol=symbol)
        for pred in prediction_results['predictions']:
            StockPrediction.objects.create(
                stock=stock,
                prediction_date=pred['date'],
                predicted_price=pred['predicted_price'],
                confidence=85.5  # Placeholder
            )
        
        return Response(prediction_results)

class WatchlistAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            watchlists = Watchlist.objects.filter(user=request.user)
            response_data = []
            
            for watchlist in watchlists:
                stocks_data = []
                for stock in watchlist.stocks.all():
                    # Get real-time data from Yahoo Finance
                    stock_data = yf.Ticker(stock.symbol)
                    if stock_data:
                        quote = stock_data.info
                        current_price = quote.get('regularMarketPrice', 0)
                        prev_close = quote.get('previousClose', 0)
                        change = current_price - prev_close
                        change_percent = (change / prev_close * 100) if prev_close else 0
                        
                        # Update stock in database
                        stock.current_price = current_price
                        stock.previous_close = prev_close
                        stock.change = change
                        stock.change_percent = change_percent
                        stock.save()
                        
                        stocks_data.append({
                            'symbol': stock.symbol,
                            'name': stock.name,
                            'current_price': float(stock.current_price),
                            'change': float(stock.change),
                            'change_percent': float(stock.change_percent)
                        })
                
                response_data.append({
                    'id': watchlist.id,
                    'name': watchlist.name,
                    'stocks': stocks_data
                })
            
            return Response(response_data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        try:
            name = request.data.get('name')
            symbols = request.data.get('symbols', [])
            
            if not name:
                return Response({'error': 'Watchlist name is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create watchlist
            watchlist = Watchlist.objects.create(user=request.user, name=name)
            
            # Add stocks to watchlist
            for symbol in symbols:
                stock_data = yf.Ticker(symbol)
                if stock_data:
                    quote = stock_data.info
                    stock, created = Stock.objects.get_or_create(
                        symbol=symbol,
                        defaults={
                            'name': quote.get('longName', f"{symbol} Company"),
                            'current_price': quote.get('regularMarketPrice', 0),
                            'previous_close': quote.get('previousClose', 0)
                        }
                    )
                    watchlist.stocks.add(stock)
            
            return Response({'message': 'Watchlist created successfully'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PortfolioAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        portfolio_items = Portfolio.objects.filter(user=request.user)
        result = []
        
        for item in portfolio_items:
            current_value = item.quantity * float(item.stock.current_price) if item.stock.current_price else 0
            invested_value = item.quantity * float(item.buy_price)
            profit_loss = current_value - invested_value
            profit_loss_percent = (profit_loss / invested_value) * 100 if invested_value > 0 else 0
            
            result.append({
                'id': item.id,
                'symbol': item.stock.symbol,
                'name': item.stock.name,
                'quantity': item.quantity,
                'buy_price': float(item.buy_price),
                'current_price': float(item.stock.current_price) if item.stock.current_price else None,
                'current_value': current_value,
                'invested_value': invested_value,
                'profit_loss': profit_loss,
                'profit_loss_percent': profit_loss_percent
            })
        
        return Response(result)
    
    def post(self, request):
        symbol = request.data.get('symbol')
        quantity = request.data.get('quantity')
        buy_price = request.data.get('buy_price')
        
        if not all([symbol, quantity, buy_price]):
            return Response({'error': 'Symbol, quantity, and buy price are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            quantity = int(quantity)
            buy_price = float(buy_price)
        except ValueError:
            return Response({'error': 'Invalid quantity or buy price'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        stock, created = Stock.objects.get_or_create(symbol=symbol, defaults={'name': f"{symbol} Company"})
        
        portfolio_item = Portfolio.objects.create(
            user=request.user,
            stock=stock,
            quantity=quantity,
            buy_price=buy_price
        )
        
        return Response({
            'id': portfolio_item.id,
            'symbol': stock.symbol,
            'quantity': portfolio_item.quantity,
            'buy_price': float(portfolio_item.buy_price),
            'message': 'Stock added to portfolio successfully'
        })


@login_required
def stock_data(request, symbol):
    # Placeholder for actual API implementation
    # This would fetch real data from a stock API
    sample_data = {
        'symbol': symbol,
        'historical_data': {
            'dates': ['2023-01-01', '2023-01-02', '2023-01-03'],
            'close': [100.0, 102.5, 101.2]
        }
    }
    return JsonResponse(sample_data)

@login_required
@require_http_methods(["POST"])
def portfolio_actions(request):
    data = json.loads(request.body)
    # Placeholder for actual implementation
    return JsonResponse({'message': 'Portfolio action successful'})

@login_required
@require_http_methods(["POST"])
def watchlist_actions(request):
    data = json.loads(request.body)
    # Placeholder for actual implementation
    return JsonResponse({'message': 'Watchlist action successful'})
