from datetime import datetime, timedelta
import requests
import pandas as pd
from config import COINGECKO_COIN_ID, MAX_RETRIES

def fetch_data(symbol="1h", timeframe="1h", limit=100):
    """
    Obtiene datos OHLC utilizando la API de CoinGecko.
    Se solicita datos de 14 días para obtener velas de 1h.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{COINGECKO_COIN_ID}/ohlc"
    params = {
        "vs_currency": "usd",
        "days": 14  # Se solicitan datos de 14 días para obtener velas de 1h
    }
    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.get(url, params=params)
            data = response.json()
            if not data or len(data) == 0:
                raise ValueError("La respuesta de la API está vacía.")
            
            # Convertir la respuesta en DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Filtrar para obtener solo los datos de los últimos 14 días
            cutoff = datetime.now() - timedelta(days=14)
            df = df[df['timestamp'] >= cutoff]
            
            if df.empty or len(df) < 2:
                raise ValueError("Datos insuficientes devueltos por la API después de filtrar.")
            
            # La API no proporciona volumen, se asigna 0
            df['volume'] = 0
            print(f"[INFO] Se obtuvieron {len(df)} registros de OHLC después de filtrar por 14 días.")
            return df
        except Exception as e:
            print(f"[Error] {e}. Reintentando... ({retries + 1}/{MAX_RETRIES})")
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
    if "bitcoin" not in data:
        raise Exception("Error obteniendo el precio de BTC.")
    return data["bitcoin"]["usd"]
