import pandas as pd
import numpy as np

def enhanced_pullback_strategy(df, long_ma=50, short_ma=20, stop_loss_pct=0.02):
    """
    Implements the enhanced pullback strategy for stock trading.
    
    Args:
        df: DataFrame with OHLC data
        long_ma: Long moving average period
        short_ma: Short moving average period
        stop_loss_pct: Stop loss percentage
        
    Returns:
        Dictionary with strategy results
    """
    df = df.copy()
    df['long_ma'] = df['close'].rolling(window=long_ma).mean()
    df['short_ma'] = df['close'].rolling(window=short_ma).mean()

    df['position'] = 0
    entry_price = 0

    for i in range(max(long_ma, short_ma), len(df)):
        if df['close'].iloc[i] > df['long_ma'].iloc[i] and df['close'].iloc[i] < df['short_ma'].iloc[i]:
            df.at[df.index[i], 'position'] = 1  # Long
            entry_price = df['close'].iloc[i]
        elif df['position'].iloc[i-1] == 1:
            # Stop Loss
            if (entry_price - df['close'].iloc[i]) / df['close'].iloc[i] > stop_loss_pct:
                df.at[df.index[i], 'position'] = 0
            elif df['close'].iloc[i] > df['short_ma'].iloc[i] and df['close'].iloc[i] < df['low'].iloc[i-1]:
                df.at[df.index[i], 'position'] = 0
            else:
                df.at[df.index[i], 'position'] = 1
        else:
            df.at[df.index[i], 'position'] = 0

    # Simulate return
    df['returns'] = df['close'].pct_change()
    df['strategy_returns'] = df['returns'] * df['position'].shift(1)

    # Calculate signals for buy/sell
    df['signal'] = 0
    df.loc[(df['position'] == 1) & (df['position'].shift(1) == 0), 'signal'] = 1  # Buy signal
    df.loc[(df['position'] == 0) & (df['position'].shift(1) == 1), 'signal'] = -1  # Sell signal

    # Calculate performance metrics
    total_return = df['strategy_returns'].sum()
    win_trades = sum(df['strategy_returns'] > 0)
    loss_trades = sum(df['strategy_returns'] < 0)
    
    # Get buy/sell signals with dates
    buy_signals = df[df['signal'] == 1].index.tolist()
    sell_signals = df[df['signal'] == -1].index.tolist()
    
    signals = []
    for date in buy_signals:
        signals.append({
            'date': date.strftime('%Y-%m-%d'),
            'type': 'BUY',
            'price': float(df.loc[date, 'close'])
        })
    
    for date in sell_signals:
        signals.append({
            'date': date.strftime('%Y-%m-%d'),
            'type': 'SELL',
            'price': float(df.loc[date, 'close'])
        })
    
    signals.sort(key=lambda x: x['date'])

    return {
        'total_return': round(total_return * 100, 2),
        'win_trades': int(win_trades),
        'loss_trades': int(loss_trades),
        'win_rate': round(win_trades / (win_trades + loss_trades) * 100, 2) if (win_trades + loss_trades) > 0 else 0,
        'signals': signals,
        'data': {
            'dates': df.index.strftime('%Y-%m-%d').tolist(),
            'close': df['close'].tolist(),
            'long_ma': df['long_ma'].tolist(),
            'short_ma': df['short_ma'].tolist(),
            'position': df['position'].tolist(),
        }
    }