import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator, ADXIndicator
from ta.volatility import BollingerBands
import requests

def calculate_indicators(data):
    """Calcula indicadores técnicos: RSI, MACD, ADX, SMAs y Bandas de Bollinger."""
    if len(data) < 2:
        raise ValueError("Datos insuficientes para calcular indicadores técnicos (se requieren al menos 2 registros).")
    
    close = data['close']
    high = data['high']
    low = data['low']
    volume = data['volume']
    
    cmf = 0
    volume_level = "N/A"
    
    sma10_series = SMAIndicator(close, window=10).sma_indicator().dropna()
    sma_10 = sma10_series.iloc[-1] if not sma10_series.empty else None
    sma25_series = SMAIndicator(close, window=25).sma_indicator().dropna()
    sma_25 = sma25_series.iloc[-1] if not sma25_series.empty else None
    sma50_series = SMAIndicator(close, window=50).sma_indicator().dropna()
    sma_50 = sma50_series.iloc[-1] if not sma50_series.empty else None

    macd_series = MACD(close).macd().dropna()
    macd = macd_series.iloc[-1] if not macd_series.empty else None
    macd_signal_series = MACD(close).macd_signal().dropna()
    macd_signal = macd_signal_series.iloc[-1] if not macd_signal_series.empty else None

    rsi_series = RSIIndicator(close, window=14).rsi().dropna()
    rsi = rsi_series.iloc[-1] if not rsi_series.empty else None

    adx_series = ADXIndicator(high, low, close).adx().dropna()
    adx = adx_series.iloc[-1] if not adx_series.empty else None

    bb_indicator = BollingerBands(close, window=20, window_dev=2)
    bb_low_series = bb_indicator.bollinger_lband().dropna()
    bb_low = bb_low_series.iloc[-1] if not bb_low_series.empty else None
    bb_medium_series = bb_indicator.bollinger_mavg().dropna()
    bb_medium = bb_medium_series.iloc[-1] if not bb_medium_series.empty else None
    bb_high_series = bb_indicator.bollinger_hband().dropna()
    bb_high = bb_high_series.iloc[-1] if not bb_high_series.empty else None

    prev_close = close.iloc[-2] if len(close) >= 2 else close.iloc[-1]

    indicators = {
        'price': close.iloc[-1],
        'rsi': rsi,
        'adx': adx,
        'macd': macd,
        'macd_signal': macd_signal,
        'sma_10': sma_10,
        'sma_25': sma_25,
        'sma_50': sma_50,
        'cmf': cmf,
        'volume_level': volume_level,
        'bb_low': bb_low,
        'bb_medium': bb_medium,
        'bb_high': bb_high,
        'prev_close': prev_close
    }
    return indicators

def check_cross_signals(data):
    """
    Detecta señales de Golden Cross o Death Cross usando SMAs de 10, 25 y 50.
    """
    close = data['close']
    if len(close) < 2:
        return False, False

    sma10 = SMAIndicator(close, window=10).sma_indicator().dropna()
    sma25 = SMAIndicator(close, window=25).sma_indicator().dropna()
    sma50 = SMAIndicator(close, window=50).sma_indicator().dropna()
    
    if len(sma10) < 2 or len(sma25) < 2 or len(sma50) < 2:
        return False, False

    sma10_prev, sma10_curr = sma10.iloc[-2], sma10.iloc[-1]
    sma25_prev, sma25_curr = sma25.iloc[-2], sma25.iloc[-1]
    sma50_prev, sma50_curr = sma50.iloc[-2], sma50.iloc[-1]
    
    golden_cross = (sma10_prev < sma25_prev and sma10_curr >= sma25_curr) and (sma25_prev < sma50_prev and sma25_curr >= sma50_curr)
    death_cross = (sma10_prev > sma25_prev and sma10_curr <= sma25_curr) and (sma25_prev > sma50_prev and sma25_curr <= sma50_curr)
    
    return golden_cross, death_cross

def fetch_btc_dominance():
    """
    Obtiene el porcentaje de dominancia de BTC desde el endpoint global de CoinGecko.
    """
    url = "https://api.coingecko.com/api/v3/global"
    response = requests.get(url)
    data = response.json()
    dominance = data['data']['market_cap_percentage'].get('btc', 0)
    return dominance
