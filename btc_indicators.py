import pandas as pd
from market import fetch_data, fetch_btc_price
from indicators import fetch_btc_dominance
from config import TIMEFRAME
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from ta.volatility import BollingerBands

def get_btc_indicators():
    """
    Calcula indicadores técnicos para BTC usando datos obtenidos de CoinGecko.
    Retorna un diccionario con:
      - Precio, RSI, MACD (y señal), SMA10, SMA25, SMA50, Bandas de Bollinger, CMF y Dominancia.
    """
    symbol = "btc"
    data = fetch_data(symbol, TIMEFRAME)
    if len(data) < 2:
        raise ValueError("Datos insuficientes para calcular indicadores técnicos de BTC.")
    close = data['close']
    high = data['high']
    low = data['low']
    price = close.iloc[-1]

    rsi_series = RSIIndicator(close, window=14).rsi().dropna()
    rsi = rsi_series.iloc[-1] if not rsi_series.empty else None

    macd_series = MACD(close).macd().dropna()
    macd = macd_series.iloc[-1] if not macd_series.empty else None
    macd_signal_series = MACD(close).macd_signal().dropna()
    macd_signal = macd_signal_series.iloc[-1] if not macd_signal_series.empty else None

    sma10_series = SMAIndicator(close, window=10).sma_indicator().dropna()
    sma_10 = sma10_series.iloc[-1] if not sma10_series.empty else None
    sma25_series = SMAIndicator(close, window=25).sma_indicator().dropna()
    sma_25 = sma25_series.iloc[-1] if not sma25_series.empty else None
    sma50_series = SMAIndicator(close, window=50).sma_indicator().dropna()
    sma_50 = sma50_series.iloc[-1] if not sma50_series.empty else None

    bb_indicator = BollingerBands(close, window=20, window_dev=2)
    bb_low_series = bb_indicator.bollinger_lband().dropna()
    bb_low = bb_low_series.iloc[-1] if not bb_low_series.empty else None
    bb_medium_series = bb_indicator.bollinger_mavg().dropna()
    bb_medium = bb_medium_series.iloc[-1] if not bb_medium_series.empty else None
    bb_high_series = bb_indicator.bollinger_hband().dropna()
    bb_high = bb_high_series.iloc[-1] if not bb_high_series.empty else None

    # Valores fijos para CMF y volumen (se pueden ajustar)
    cmf = 0
    volume_level = "N/A"
    dominance = fetch_btc_dominance()

    indicators = {
        'price': price,
        'rsi': rsi,
        'macd': macd,
        'macd_signal': macd_signal,
        'sma_10': sma_10,
        'sma_25': sma_25,
        'sma_50': sma_50,
        'bb_low': bb_low,
        'bb_medium': bb_medium,
        'bb_high': bb_high,
        'cmf': cmf,
        'volume_level': volume_level,
        'dominance': dominance
    }
    return indicators
