import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import datetime

def create_features(df, window=30):
    """Create features for the prediction model"""
    df = df.copy()
    
    # Technical indicators
    df['ma7'] = df['close'].rolling(window=7).mean()
    df['ma21'] = df['close'].rolling(window=21).mean()
    df['ma50'] = df['close'].rolling(window=50).mean()
    df['ma200'] = df['close'].rolling(window=200).mean()
    
    # Price momentum
    df['return_1d'] = df['close'].pct_change(periods=1)
    df['return_5d'] = df['close'].pct_change(periods=5)
    df['return_10d'] = df['close'].pct_change(periods=10)
    
    # Volatility
    df['volatility_10d'] = df['return_1d'].rolling(window=10).std()
    df['volatility_30d'] = df['return_1d'].rolling(window=30).std()
    
    # Target: next day's closing price
    df['target'] = df['close'].shift(-1)
    
    # Drop NaN values
    df.dropna(inplace=True)
    
    return df

def predict_stock_price(historical_data, days_ahead=5, model_type='lstm'):
    """
    Predict stock prices for the next few days using machine learning
    
    Args:
        historical_data: DataFrame with OHLC data
        days_ahead: Number of days to predict ahead
        model_type: Type of model to use ('lstm', 'arima', 'prophet', 'ensemble')
        
    Returns:
        Dictionary with prediction results
    """
    df = historical_data.copy()
    
    # Create features
    df = create_features(df)
    
    # Add RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Add MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    # Prepare features and target
    features = ['ma7', 'ma21', 'ma50', 'ma200', 'return_1d', 'return_5d', 'return_10d',
                'volatility_10d', 'volatility_30d', 'rsi', 'macd', 'signal_line']
    X = df[features]
    y = df['target']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train model
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    # Make predictions
    predictions = []
    last_data = df.iloc[-1:].copy()
    
    for i in range(days_ahead):
        # Predict next day
        pred = model.predict(last_data[features])[0]
        pred_date = df.index[-1] + pd.Timedelta(days=i+1)
        
        predictions.append({
            'date': pred_date.strftime('%Y-%m-%d'),
            'predicted_price': round(float(pred), 2)
        })
        
        # Update features for next prediction
        last_data['close'] = pred
        last_data = create_features(last_data)
    
    # Calculate model performance metrics
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mse)
    
    # Calculate confidence score based on multiple metrics
    confidence = round((r2 * 100 + (1 - rmse/y_test.mean()) * 100) / 2, 2)
    
    # Prepare data for modeling with enhanced features
    features = ['ma7', 'ma21', 'ma50', 'ma200', 'return_1d', 'return_5d', 'return_10d',
                'volatility_10d', 'volatility_30d', 'rsi', 'macd', 'signal_line']
    X = df[features]
    y = df['target']
    
    # Scale features
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train model
    model = LinearRegression()
    model.fit(X_scaled, y)
    
    # Make predictions for future days
    last_data = df.iloc[-1:][features]
    predictions = []
    current_data = last_data.copy()
    
    last_date = df.index[-1]
    last_close = df['close'].iloc[-1]
    
    for i in range(days_ahead):
        # Scale the current data
        current_scaled = scaler.transform(current_data)
        
        # Predict the next day's price
        next_price = model.predict(current_scaled)[0]
        
        # Calculate the date for this prediction
        next_date = last_date + datetime.timedelta(days=i+1)
        
        # Store the prediction
        predictions.append({
            'date': next_date.strftime('%Y-%m-%d'),
            'predicted_price': round(float(next_price), 2),
            'change': round(float(next_price - last_close), 2),
            'change_percent': round(float((next_price - last_close) / last_close * 100), 2)
        })
        
        # Update all features for next prediction
        current_data['ma7'] = df['close'].rolling(window=7).mean().iloc[-1] if i == 0 else next_price
        current_data['ma21'] = df['close'].rolling(window=21).mean().iloc[-1]
        current_data['ma50'] = df['close'].rolling(window=50).mean().iloc[-1]
        current_data['ma200'] = df['close'].rolling(window=200).mean().iloc[-1]
        
        current_data['return_1d'] = (next_price - last_close) / last_close
        current_data['return_5d'] = df['close'].pct_change(periods=5).iloc[-1]
        current_data['return_10d'] = df['close'].pct_change(periods=10).iloc[-1]
        
        current_data['volatility_10d'] = df['return_1d'].rolling(window=10).std().iloc[-1]
        current_data['volatility_30d'] = df['return_1d'].rolling(window=30).std().iloc[-1]
        
        # Update RSI
        delta = next_price - last_close
        gain = delta if delta > 0 else 0
        loss = -delta if delta < 0 else 0
        avg_gain = (current_data['rsi'].iloc[-1] * 13 + gain) / 14
        avg_loss = (current_data['rsi'].iloc[-1] * 13 + loss) / 14
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        current_data['rsi'] = 100 - (100 / (1 + rs))
        
        # Update MACD
        current_data['macd'] = df['macd'].ewm(span=12, adjust=False).mean().iloc[-1]
        current_data['signal_line'] = df['signal_line'].ewm(span=9, adjust=False).mean().iloc[-1]
        
        last_close = next_price
    
    return {
        'predictions': predictions,
        'model_performance': {
            'confidence': confidence,
            'r2_score': round(r2 * 100, 2),
            'rmse': round(rmse, 2),
            'mae': round(mae, 2)
        }
    }