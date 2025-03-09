import os

# Columnas utilizadas para cálculos
feature_columns = ['open', 'high', 'low', 'close', 'volume', 'sma_25', 'bb_low', 'bb_medium', 'bb_high']

# --- Configuración de APIs y parámetros ---
# CoinGecko: Define el activo a consultar y la API key (si la tienes)
COINGECKO_COIN_ID = os.getenv("COINGECKO_COIN_ID", "binancecoin")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")  # Pon aquí tu API key de CoinGecko

# Configuración de Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")  # Pon aquí tu token de Telegram
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # Pon aquí el chat id (puede ser de grupo o canal)

# API de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # Pon aquí tu API key de OpenAI

# Configuración del mercado
SYMBOL = os.getenv("SYMBOL", "BNB/USDT")  # Símbolo que usas en el análisis
TIMEFRAME = os.getenv("TIMEFRAME", "1h")   # Temporalidad de las velas
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
