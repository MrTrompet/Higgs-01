# market.py
import requests
import pandas as pd
from config import COINGECKO_COIN_ID, TIMEFRAME, MAX_RETRIES

def fetch_data(symbol=TIMEFRAME, timeframe=TIMEFRAME, limit=100):
    """
    Obtiene datos OHLC utilizando la API de CoinGecko.
    Para TIMEFRAME='1h', se usa el endpoint /ohlc con days=1 (candles de 1h).
    """
    url = f"https://api.coingecko.com/api/v3/coins/{COINGECKO_COIN_ID}/ohlc"
    params = {
        "vs_currency": "usd",
        "days": 1  # Datos de 1 día (candles de 1h)
    }
    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.get(url, params=params)
            data = response.json()
            # Formato de cada vela: [timestamp, open, high, low, close]
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            # La API no proporciona volumen, se asigna 0
            df['volume'] = 0
            return df
        except Exception as e:
            print(f"[Error] {e}. Reintentando...")
            retries += 1
    raise Exception("No se pudieron obtener datos tras varios intentos.")

def fetch_btc_price():
    """
    Obtiene el precio actual de BTC en USD usando CoinGecko.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "bitcoin", "vs_currencies": "usd"}
    response = requests.get(url, params=params)
    data = response.json()
    return data["bitcoin"]["usd"]
