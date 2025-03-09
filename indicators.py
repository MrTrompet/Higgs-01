# indicators.py
import pandas as pd
import requests
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator, ADXIndicator
from ta.volatility import BollingerBands

def calculate_indicators(data):
    """Calcula indicadores técnicos: RSI, MACD, ADX, SMAs y Bandas de Bollinger."""
    close = data['close']
    high = data['high']
    low = data['low']
    volume = data['volume']
    
    # Dado que no se dispone de volumen real, se asigna un valor neutro
    cmf = 0
    volume_level = "N/A"

    sma_10 = SMAIndicator(close, window=10).sma_indicator().iloc[-1]
    sma_25 = SMAIndicator(close, window=25).sma_indicator().iloc[-1]
    sma_50 = SMAIndicator(close, window=50).sma_indicator().iloc[-1]

    macd_indicator = MACD(close)
    macd = macd_indicator.macd().iloc[-1]
    macd_signal = macd_indicator.macd_signal().iloc[-1]

    rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
    adx = ADXIndicator(high, low, close).adx().iloc[-1]

    bb_indicator = BollingerBands(close, window=20, window_dev=2)
    bb_low = bb_indicator.bollinger_lband().iloc[-1]
    bb_medium = bb_indicator.bollinger_mavg().iloc[-1]
    bb_high = bb_indicator.bollinger_hband().iloc[-1]

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
        'prev_close': close.iloc[-2] if len(close) >= 2 else close.iloc[-1]
    }
    return indicators

def check_cross_signals(data):
    """
    Detecta señales de Golden Cross o Death Cross usando SMAs de 10, 25 y 50.
    Se comparan los valores de las últimas dos velas para identificar el cruce.
    """
    close = data['close']
    sma10 = SMAIndicator(close, window=10).sma_indicator()
    sma25 = SMAIndicator(close, window=25).sma_indicator()
    sma50 = SMAIndicator(close, window=50).sma_indicator()
    
    if len(close) < 2:
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
