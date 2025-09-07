import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import percentileofscore
from datetime import datetime, timedelta
import matplotlib.pyplot as plt  # For visualization

class StopHunterVS:
    def __init__(self):
        self.liquidity_zones = {}
        
    def get_data(self, ticker, period='1d', interval='5m'):
        """Robust data fetching with error handling"""
        try:
            data = yf.download(ticker, period=period, interval=interval, progress=False)
            if data.empty:
                raise ValueError(f"No data returned for {ticker}")
            return data
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

    def plot_liquidity(self, ticker):
        """Visualize liquidity zones"""
        data = self.get_data(ticker, '20d', '1d')
        if data is None:
            return
            
        plt.figure(figsize=(12,6))
        plt.plot(data['Close'], label='Price')
        
        # Plot liquidity zones
        lz = self.identify_liquidity_pools(ticker)
        plt.axhline(lz['recent_low'], color='green', linestyle='--', alpha=0.5, label='Support')
        plt.axhline(lz['recent_high'], color='red', linestyle='--', alpha=0.5, label='Resistance')
        
        for node in lz['high_volume_nodes']:
            plt.axhline(node, color='purple', linestyle=':', alpha=0.3, label='Volume Cluster')
            
        plt.title(f"{ticker} Liquidity Zones")
        plt.legend()
        plt.show()

    def identify_liquidity_pools(self, ticker):
        """Enhanced liquidity detection"""
        data = self.get_data(ticker, '20d', '1d')
        if data is None:
            return {}
            
        # Calculate key levels
        self.liquidity_zones[ticker] = {
            'recent_low': data['Low'].min(),
            'recent_high': data['High'].max(),
            'high_volume_nodes': self._find_volume_clusters(data),
            'vwap': self._calculate_vwap(data)
        }
        return self.liquidity_zones[ticker]

    def _calculate_vwap(self, df):
        """Volume Weighted Average Price"""
        return (df['Volume'] * (df['High'] + df['Low'] + df['Close'])/3).sum() / df['Volume'].sum()

    def _find_volume_clusters(self, df):
        """Improved volume node detection"""
        try:
            bins = np.linspace(df['Low'].min(), df['High'].max(), 20)
            hist, edges = np.histogram(df['Close'], bins=bins, weights=df['Volume'])
            return [round(edge, 2) for edge in edges[np.argsort(hist)[-3:]]]
        except:
            return []

    def scan_market(self, tickers):
        """Multi-asset scanner"""
        results = {}
        for ticker in tickers:
            signals = self.detect_stop_hunt(ticker)
            if signals:
                results[ticker] = signals
        return results

    def detect_stop_hunt(self, ticker):
        """Main detection logic"""
        intraday = self.get_data(ticker)
        if intraday is None:
            return []
            
        lz = self.identify_liquidity_pools(ticker)
        if not lz:
            return []
            
        current = intraday.iloc[-1]
        signals = []
        
        # Bear trap detection (false breakdown)
        if (current['Low'] <= lz['recent_low'] * 1.005 and 
            current['Close'] > lz['recent_low'] and
            current['Volume'] > intraday['Volume'].mean() * 1.8):
            signals.append({
                'type': 'bear_trap',
                'entry': round(current['Close'], 2),
                'stop': round(lz['recent_low'] * 0.995, 2),
                'target': round(lz['vwap'], 2),
                'confidence': min(90, self._calculate_confidence(intraday, 'down') * 100)
            })
        
        # Bull trap detection (false breakout)
        if (current['High'] >= lz['recent_high'] * 0.995 and 
            current['Close'] < lz['recent_high'] and
            current['Volume'] > intraday['Volume'].mean() * 1.8):
            signals.append({
                'type': 'bull_trap',
                'entry': round(current['Close'], 2),
                'stop': round(lz['recent_high'] * 1.005, 2),
                'target': round(lz['vwap'], 2),
                'confidence': min(90, self._calculate_confidence(intraday, 'up') * 100)
            })
            
        return signals

    def _calculate_confidence(self, df, direction):
        """Improved confidence metric"""
        returns = np.log(df['Close']).diff()
        if direction == 'down':
            return percentileofscore(returns, returns.iloc[-1])/100
        else:
            return 1 - percentileofscore(returns, returns.iloc[-1])/100

# VS Code Execution Block
if __name__ == "__main__":
    print("VS Code Stop Hunter Activated\n")
    
    analyzer = StopHunterVS()
    
    # Configure your watchlist
    watchlist = ['RELIANCE.NS', 'TATASTEEL.NS', 'HDFCBANK.NS', 'ICICIBANK.NS']
    
    while True:
        print("\n" + "="*50)
        print(f"Scanning at {datetime.now().strftime('%H:%M:%S')}")
        print("="*50)
        
        results = analyzer.scan_market(watchlist)
        
        if results:
            for ticker, signals in results.items():
                print(f"\n🔥 {ticker}")
                for sig in signals:
                    print(f"  {sig['type'].upper()} Signal")
                    print(f"  Entry: {sig['entry']} | Stop: {sig['stop']}")
                    print(f"  Target: {sig['target']} | Confidence: {sig['confidence']}%")
                    
                    # Visualize the opportunity
                    analyzer.plot_liquidity(ticker)
        else:
            print("\nNo stop runs detected in current watchlist")
            
        # Refresh every 5 minutes
        import time
        time.sleep(300)