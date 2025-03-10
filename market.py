from datetime import datetime, timedelta
import requests
import pandas as pd
from config import COINGECKO_COIN_ID, COINGECKO_API_KEY, MAX_RETRIES

# Diccionario para mapear símbolos cortos a IDs oficiales de CoinGecko
COIN_ID_MAP = {
    "bnb": "binancecoin",
    "btc": "bitcoin"
    # Agrega otros mapeos según sea necesario
}

def fetch_data(symbol=None, timeframe="1h", days=14):
    """
    Obtiene datos OHLC utilizando la API de CoinGecko.
    
    Parámetros:
      - symbol: ID o símbolo corto de la moneda en CoinGecko (ej. "bitcoin", "bnb", etc.). 
                Si no se especifica, se utiliza COINGECKO_COIN_ID del config.
      - timeframe: Intervalo de tiempo de las velas (por ejemplo, "1h"). Actualmente no se utiliza
                   para modificar la consulta, ya que CoinGecko determina el intervalo en función del parámetro "days".
      - days: Número de días de datos a obtener. Por defecto se solicitan 14 días.
      
    Se envía la API key en el header.
    """
    if symbol is not None:
        # Si el símbolo contiene una barra (ej. "BNB/USDT"), se toma solo la parte anterior a la barra
        symbol = symbol.split('/')[0]
        # Convertir a minúsculas y mapear al ID oficial usando el diccionario
        coin_id = COIN_ID_MAP.get(symbol.lower(), symbol.lower())
    else:
        coin_id = COINGECKO_COIN_ID

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
