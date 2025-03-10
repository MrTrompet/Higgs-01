from datetime import datetime, timedelta
import requests
import pandas as pd
from config import COINGECKO_COIN_ID, COINGECKO_API_KEY, MAX_RETRIES

def fetch_data(symbol=None, timeframe="1h", days=14):
    """
    Obtiene datos OHLC utilizando la API de CoinGecko.
    
    Parámetros:
      - symbol: ID de la moneda en CoinGecko (ej. "bitcoin", "binancecoin", etc.). 
                Si no se especifica, se utiliza COINGECKO_COIN_ID del config.
      - timeframe: Intervalo de tiempo de las velas (por ejemplo, "1h"). Actualmente no se utiliza
                   para modificar la consulta, ya que CoinGecko determina el intervalo en función del parámetro "days".
      - days: Número de días de datos a obtener. Por defecto se solicitan 14 días.
      
    Se envía la API key en el header.
    """
    coin_id = symbol if symbol is not None else COINGECKO_COIN_ID
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    params = {
        "vs_currency": "usd",
        "days": days
    }
    headers = {"x_cg_pro_api_key": COINGECKO_API_KEY}
    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()  # Verifica que la respuesta sea 200 OK
            data = response.json()
            if not data or len(data) == 0:
                raise ValueError("La respuesta de la API está vacía.")
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            if df.empty or len(df) < 2:
                raise ValueError("Datos insuficientes devueltos por la API.")
            df['volume'] = 0  # La API no proporciona volumen
            print(f"[INFO] Se obtuvieron {len(df)} registros de OHLC para {coin_id}.")
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
    response.raise_for_status()
    data = response.json()
    if "bitcoin" not in data:
        raise Exception("Error obteniendo el precio de BTC.")
    return data["bitcoin"]["usd"]

def fetch_historical_data(symbol=None, timeframe="1h", days=14):
    """
    Obtiene datos históricos utilizando fetch_data.
    
    Parámetros:
      - symbol: ID de la moneda en CoinGecko (ej. "bitcoin", "binancecoin", etc.).
      - timeframe: Intervalo de las velas (por ejemplo, "1h").
      - days: Número de días de datos a obtener.
    """
    return fetch_data(symbol, timeframe, days)
