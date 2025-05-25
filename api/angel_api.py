from SmartApi import SmartConnect
import pandas as pd
import logging
import yfinance as yf
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AngelBrokingAPI:
    def __init__(self):
        self.api_key = "9qBojzpf"
        self.secret_key = "fe49e2e1-20bb-4535-9013-e9da28e957c8"
        self.smart_api = None
        self.session_token = None
        self.refresh_token = None
        self.feed_token = None
        
    def search_stocks(self, query):
        try:
            # Try to get data from Yahoo Finance API
            stocks = []
            tickers = yf.Tickers(query)
            
            for symbol in query.split():
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    if info:
                        stock_data = {
                            'symbol': symbol.upper(),
                            'name': info.get('longName', ''),
                            'current_price': info.get('currentPrice', 0.0),
                            'previous_close': info.get('previousClose', 0.0),
                            'change': round(info.get('currentPrice', 0.0) - info.get('previousClose', 0.0), 2),
                            'change_percent': round(((info.get('currentPrice', 0.0) - info.get('previousClose', 0.0)) / info.get('previousClose', 1.0)) * 100, 2)
                        }
                        stocks.append(stock_data)
                except Exception as e:
                    logger.error(f"Error fetching data for {symbol}: {str(e)}")
                    continue
            
            return stocks
        except Exception as e:
            logger.error(f"Error in stock search: {str(e)}")
            return []
        
    def login(self, client_id, password, totp):
        try:
            self.smart_api = SmartConnect(api_key=self.api_key)
            data = self.smart_api.generateSession(client_id, password, totp)
            self.session_token = data['data']['jwtToken']
            self.refresh_token = data['data']['refreshToken']
            self.feed_token = self.smart_api.getfeedToken()
            return True
        except Exception as e:
            logger.error(f"Error in login: {str(e)}")
            return False
    
    def get_profile(self):
        try:
            return self.smart_api.getProfile()
        except Exception as e:
            logger.error(f"Error getting profile: {str(e)}")
            return None
    
    def get_historical_data(self, symbol, exchange, interval, from_date, to_date):
        try:
            historic_param = {
                "exchange": exchange,
                "symboltoken": self.get_token(symbol, exchange),
                "interval": interval,
                "fromdate": from_date,
                "todate": to_date
            }
            history_data = self.smart_api.getCandleData(historic_param)
            if history_data and 'data' in history_data:
                df = pd.DataFrame(history_data['data'], 
                                 columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                return df
            return None
        except Exception as e:
            logger.error(f"Error getting historical data: {str(e)}")
            return None
    
    def get_token(self, symbol, exchange):
        try:
            # This is a simplified approach. In a real app, you'd need to handle token mapping
            # or use the Angel Broking API to get the token for a symbol
            return "12345"  # Placeholder
        except Exception as e:
            logger.error(f"Error getting token: {str(e)}")
            return None
    
    def get_ltp(self, symbol, exchange):
        try:
            param = {
                "exchange": exchange,
                "tradingsymbol": symbol,
                "symboltoken": self.get_token(symbol, exchange)
            }
            return self.smart_api.ltpData(param)
        except Exception as e:
            logger.error(f"Error getting LTP: {str(e)}")
            return None
    
    def place_order(self, symbol, exchange, transaction_type, quantity, price=0, order_type="MARKET"):
        try:
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": symbol,
                "symboltoken": self.get_token(symbol, exchange),
                "transactiontype": transaction_type,
                "exchange": exchange,
                "ordertype": order_type,
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": price,
                "squareoff": "0",
                "stoploss": "0",
                "quantity": quantity
            }
            return self.smart_api.placeOrder(order_params)
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return None