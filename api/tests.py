from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from stocks.models import Stock, Watchlist, Portfolio, StockNews, StockPrediction, TradeSignal
from decimal import Decimal
import json
import yfinance as yf

class StockDataAPITests(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test stock
        self.stock = Stock.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            current_price=Decimal('150.00'),
            previous_close=Decimal('148.00'),
            change=Decimal('2.00'),
            change_percent=Decimal('1.35')
        )
    
    @patch('yfinance.Ticker')
    def test_get_stock_data_success(self, mock_ticker):
        # Mock yfinance response
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {
            'regularMarketPrice': 150.00,
            'previousClose': 148.00,
            'longName': 'Apple Inc.',
            'sector': 'Technology',
            'industry': 'Consumer Electronics'
        }
        mock_ticker.return_value = mock_ticker_instance
        
        url = reverse('api:stock_data', args=['AAPL'])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['symbol'], 'AAPL')
        self.assertEqual(response.data['name'], 'Apple Inc.')
        
    def test_get_stock_data_invalid_symbol(self):
        url = reverse('api:stock_data', args=['INVALID'])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_get_stock_data_unauthenticated(self):
        self.client.force_authenticate(user=None)
        url = reverse('api:stock_data', args=['AAPL'])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class WatchlistAPITests(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test stock
        self.stock = Stock.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            current_price=Decimal('150.00')
        )
        
        # Create test watchlist
        self.watchlist = Watchlist.objects.create(
            user=self.user,
            name='Test Watchlist'
        )
        self.watchlist.stocks.add(self.stock)
    
    def test_get_watchlists(self):
        url = reverse('api:watchlist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Test Watchlist')
    
    def test_create_watchlist(self):
        url = reverse('api:watchlist')
        data = {
            'name': 'New Watchlist',
            'symbols': ['GOOGL']
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Watchlist.objects.count(), 2)

class PortfolioAPITests(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test stock
        self.stock = Stock.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            current_price=Decimal('150.00')
        )
        
        # Create test portfolio item
        self.portfolio_item = Portfolio.objects.create(
            user=self.user,
            stock=self.stock,
            quantity=10,
            buy_price=Decimal('145.00')
        )
    
    def test_get_portfolio(self):
        url = reverse('api:portfolio')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['symbol'], 'AAPL')
        self.assertEqual(response.data[0]['quantity'], 10)
    
    def test_portfolio_calculations(self):
        url = reverse('api:portfolio')
        response = self.client.get(url)
        
        item = response.data[0]
        self.assertEqual(item['current_value'], float(self.portfolio_item.quantity * self.stock.current_price))
        self.assertEqual(item['invested_value'], float(self.portfolio_item.quantity * self.portfolio_item.buy_price))

class PredictionAPITests(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test stock
        self.stock = Stock.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            current_price=Decimal('150.00')
        )
    
    @patch('api.prediction.predict_stock_price')
    def test_get_prediction(self, mock_predict):
        mock_predict.return_value = {
            'predictions': [
                {'date': '2024-01-01', 'predicted_price': 155.00}
            ]
        }
        
        url = reverse('api:prediction', args=['AAPL'])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('predictions', response.data)
