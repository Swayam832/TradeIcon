from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from stocks.models import Stock, Watchlist
import yfinance as yf
import logging

class WatchlistAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            watchlists = Watchlist.objects.filter(user=request.user)
            watchlist_data = []
            
            for watchlist in watchlists:
                stocks_data = [{
                    'symbol': stock.symbol,
                    'name': stock.name,
                    'current_price': stock.current_price,
                    'change': stock.change,
                    'change_percent': stock.change_percent
                } for stock in watchlist.stocks.all()]
                
                watchlist_data.append({
                    'id': watchlist.id,
                    'name': watchlist.name,
                    'stocks': stocks_data
                })
            
            return Response(watchlist_data)
            
        except Exception as e:
            logger.error(f"Error fetching watchlists: {str(e)}")
            return Response({'error': 'An error occurred while fetching watchlists'}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        try:
            name = request.data.get('name')
            
            if not name:
                return Response({'error': 'Watchlist name is required'}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            watchlist = Watchlist.objects.create(user=request.user, name=name)
            
            return Response({
                'id': watchlist.id,
                'name': watchlist.name,
                'message': 'Watchlist created successfully'
            })
            
        except Exception as e:
            logger.error(f"Error creating watchlist: {str(e)}")
            return Response({'error': 'An error occurred while creating watchlist'}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_stock_to_watchlist(request):
    try:
        watchlist_id = request.data.get('watchlist_id')
        symbol = request.data.get('symbol')

        if not watchlist_id or not symbol:
            return Response({'error': 'Watchlist ID and symbol are required'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        watchlist = Watchlist.objects.filter(id=watchlist_id, user=request.user).first()
        if not watchlist:
            return Response({'error': 'Watchlist not found'}, 
                            status=status.HTTP_404_NOT_FOUND)

        # Get stock data from Yahoo Finance
        try:
            stock_data = yf.Ticker(symbol)
            info = stock_data.info
            
            if not info or 'symbol' not in info:
                return Response({'error': 'Invalid stock symbol'}, 
                                status=status.HTTP_400_BAD_REQUEST)

            # Create or update stock
            stock, created = Stock.objects.update_or_create(
                symbol=symbol,
                defaults={
                    'name': info.get('longName', info.get('shortName', f'{symbol} Company')),
                    'current_price': info.get('regularMarketPrice', 0),
                    'previous_close': info.get('regularMarketPreviousClose', 0),
                    'change': info.get('regularMarketChange', 0),
                    'change_percent': info.get('regularMarketChangePercent', 0)
                }
            )

            # Add stock to watchlist
            watchlist.stocks.add(stock)
            
            return Response({'message': 'Stock added to watchlist successfully'})

        except Exception as e:
            logger.error(f"Error fetching stock data for {symbol}: {str(e)}")
            return Response({'error': 'Error fetching stock data'}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"Error adding stock to watchlist: {str(e)}")
        return Response({'error': 'An error occurred'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_stock_from_watchlist(request):
    try:
        watchlist_id = request.data.get('watchlist_id')
        symbol = request.data.get('symbol')

        if not watchlist_id or not symbol:
            return Response({'error': 'Watchlist ID and symbol are required'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        watchlist = Watchlist.objects.filter(id=watchlist_id, user=request.user).first()
        if not watchlist:
            return Response({'error': 'Watchlist not found'}, 
                            status=status.HTTP_404_NOT_FOUND)

        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            return Response({'error': 'Stock not found'}, 
                            status=status.HTTP_404_NOT_FOUND)

        watchlist.stocks.remove(stock)
        return Response({'message': 'Stock removed from watchlist successfully'})

    except Exception as e:
        logger.error(f"Error removing stock from watchlist: {str(e)}")
        return Response({'error': 'An error occurred'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def edit_watchlist(request):
    try:
        watchlist_id = request.data.get('id')
        name = request.data.get('name')

        if not watchlist_id or not name:
            return Response({'error': 'Watchlist ID and name are required'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        watchlist = Watchlist.objects.filter(id=watchlist_id, user=request.user).first()
        if not watchlist:
            return Response({'error': 'Watchlist not found'}, 
                            status=status.HTTP_404_NOT_FOUND)

        watchlist.name = name
        watchlist.save()

        return Response({'message': 'Watchlist updated successfully'})

    except Exception as e:
        logger.error(f"Error editing watchlist: {str(e)}")
        return Response({'error': 'An error occurred'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_watchlist(request):
    try:
        watchlist_id = request.data.get('id')

        if not watchlist_id:
            return Response({'error': 'Watchlist ID is required'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        watchlist = Watchlist.objects.filter(id=watchlist_id, user=request.user).first()
        if not watchlist:
            return Response({'error': 'Watchlist not found'}, 
                            status=status.HTTP_404_NOT_FOUND)

        watchlist.delete()
        return Response({'message': 'Watchlist deleted successfully'})

    except Exception as e:
        logger.error(f"Error deleting watchlist: {str(e)}")
        return Response({'error': 'An error occurred'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)