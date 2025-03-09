import os

# Columnas utilizadas para cálculos (se mantienen para compatibilidad)
feature_columns = ['open', 'high', 'low', 'close', 'volume', 'sma_25', 'bb_low', 'bb_medium', 'bb_high']

# --- Configuración de APIs y parámetros ---
# Si las variables de entorno no están definidas, se usan valores por defecto (p.ej., para pruebas locales)
COINGECKO_COIN_ID = os.getenv("COINGECKO_COIN_ID", "binancecoin")

# Configuración de Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "tu_token_de_telegram_aquí")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-4726165466")

# API de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "tu_openai_api_key_aquí")

# Configuración del mercado
TIMEFRAME = os.getenv("TIMEFRAME", "1h")      # Temporalidad de las velas
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))  # Número máximo de reintentos en la consulta
