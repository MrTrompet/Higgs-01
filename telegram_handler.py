import requests
import openai
import time
from langdetect import detect
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, OPENAI_API_KEY, SYMBOL, TIMEFRAME
from market import fetch_data
from indicators import calculate_indicators

openai.api_key = OPENAI_API_KEY

# Definir START_TIME como el momento en que se inicia este módulo (en Unix timestamp)
START_TIME = int(time.time())

def send_telegram_message(message, chat_id=None):
    """Envía un mensaje al chat de Telegram."""
    if not chat_id:
        chat_id = TELEGRAM_CHAT_ID  # Usar el chat grupal por defecto
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message}  # Sin parse_mode para enviar texto plano
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Error al enviar mensaje a Telegram: {response.text}")
    except Exception as e:
        print(f"Error en la conexión con Telegram: {e}")

def detect_language(text):
    """
    Detección del idioma usando langdetect.
    Retorna 'es' si se detecta español, 'en' en caso contrario.
    """
    try:
        lang = detect(text)
        return 'es' if lang == 'es' else 'en'
    except:
        # Si hay un error en la detección, asumir inglés por defecto
        return 'en'

def handle_telegram_message(update):
    """
    Procesa los mensajes recibidos en Telegram y responde usando GPT-4 de OpenAI.
    Higgs X se presenta como el agente de inteligencia del escuadrón encargado y se dirige al usuario utilizando su nombre o username.
    Además, si se detecta una petición de gráfico, se llama a PrintGraphic.py.
    Solo procesa mensajes nuevos (con fecha posterior a START_TIME).
    """
    message_obj = update.get("message", {})
    message_text = message_obj.get("text", "").strip()
    chat_id = message_obj.get("chat", {}).get("id")
    user_data = message_obj.get("from", {})
    # Se intenta obtener el username, pero si no existe se usa el first_name
    username = user_data.get("username") or user_data.get("first_name", "Agente")
    message_date = message_obj.get("date", 0)  # Unix timestamp

    if not message_text or not chat_id:
        return

    # Definir msg_lower para evitar conflictos de nombres
    msg_lower = message_text.lower()

    # Si se solicita un gráfico de liquidaciones o liquidez
    if any(phrase in msg_lower for phrase in ["liquidacion", "liquidez", "liquidaciones"]):
        from PrintGraphic import send_liquidation_graph, extract_timeframe
        timeframe = extract_timeframe(msg_lower)  # Extrae, por ejemplo, "1h"
        send_liquidation_graph(chat_id, timeframe)
        return

    # Ignorar mensajes antiguos
    if message_date < START_TIME:
        return

    # Si se solicita un gráfico (velas o lineal)
    if any(phrase in msg_lower for phrase in ["grafico", "gráfico"]):
        from PrintGraphic import send_graphic, extract_timeframe
        # Extraer la temporalidad solicitada usando la función extract_timeframe
        timeframe = extract_timeframe(msg_lower)
        # Determinar el tipo de gráfico: buscar palabras clave para candlestick
        chart_type = "line"
        if any(keyword in msg_lower for keyword in ["vela", "velas", "candlestick", "japonesas"]):
            chart_type = "candlestick"
        send_graphic(chat_id, timeframe, chart_type)
        return

    # Detección del idioma del mensaje
    language = detect_language(message_text)

    # Obtener datos de Binance (por ejemplo, SOL/USDT) y calcular indicadores
    data = fetch_data(SYMBOL, TIMEFRAME)
    indicators = calculate_indicators(data)

    # Crear el contexto y el prompt según el idioma
    if language == 'es':
        system_prompt = (
            "Eres Higgs X, el agente de inteligencia del escuadrón encargado de vigilar el ecosistema de Virtuals. "
            "Cuando respondas, preséntate siempre como 'Higgs X' y dirige tus mensajes al usuario utilizando su nombre, "
            "por ejemplo, 'agente @mrtrompet'. No confundas al usuario con tu identidad; tú eres Higgs X. "
            "Responde de forma concisa, seria y con un toque de misterio."
        )
        context = (
            f"Hola agente @{username}, aquí Higgs X al habla. Mi misión es vigilar el ecosistema de Virtuals, "
            "rastrear a las ballenas y mantener informado al escuadrón sobre cada fluctuación del mercado en tiempo real."
            "\n\n"
            f"Indicadores técnicos actualizados de {SYMBOL}:\n"
            f"- Precio actual: ${indicators['price']:.2f}\n"
            f"- RSI: {indicators['rsi']:.2f}\n"
            f"- MACD: {indicators['macd']:.2f} (Señal: {indicators['macd_signal']:.2f})\n"
            f"- SMA10: {indicators['sma_10']:.2f} | SMA25: {indicators['sma_25']:.2f} | SMA50: {indicators['sma_50']:.2f}\n"
            f"- Volumen: {indicators['volume_level']} (CMF: {indicators['cmf']:.2f})\n\n"
            "Bandas de Bollinger:\n"
            f"Low: ${indicators['bb_low']:.2f}\n"
            f"Medium: ${indicators['bb_medium']:.2f}\n"
            f"High: ${indicators['bb_high']:.2f}\n\n"
            f"Pregunta: {message_text}"
        )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            max_tokens=500,
            temperature=0.7,
            stop=None
        )
        answer = response.choices[0].message.content.strip()
        # Escapar manualmente caracteres problemáticos
        answer = answer.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
    except Exception as e:
        answer = f"⚠️ Error al procesar la solicitud: {e}"

    send_telegram_message(answer, chat_id)

def get_updates():
    """Obtiene los últimos mensajes enviados al bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Retornar sólo actualizaciones con fecha >= START_TIME
            updates = response.json().get("result", [])
            return [upd for upd in updates if upd.get("message", {}).get("date", 0) >= START_TIME]
        else:
            print(f"Error al obtener actualizaciones: {response.text}")
            return []
    except Exception as e:
        print(f"Error en la conexión con Telegram: {e}")
        return []
