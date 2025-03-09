import requests
import openai
import time
from langdetect import detect
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, OPENAI_API_KEY, SYMBOL, TIMEFRAME
from market import fetch_data, fetch_btc_price
from indicators import calculate_indicators, fetch_btc_dominance
from ml_model import aggregate_signals

openai.api_key = OPENAI_API_KEY

# Definir START_TIME como el momento en que se inicia este módulo (en Unix timestamp)
START_TIME = int(time.time())

def send_telegram_message(message, chat_id=None):
    """Envía un mensaje al chat de Telegram."""
    if not chat_id:
        chat_id = TELEGRAM_CHAT_ID  # Usa el chat grupal por defecto
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"[Error] Al enviar mensaje a Telegram: {response.text}")
    except Exception as e:
        print(f"[Error] En la conexión con Telegram: {e}")

def detect_language(text):
    """
    Detección del idioma usando langdetect.
    Retorna 'es' si se detecta español, 'en' en caso contrario.
    """
    try:
        lang = detect(text)
        return 'es' if lang == 'es' else 'en'
    except Exception as e:
        print(f"[Error] detect_language: {e}")
        return 'en'

def handle_telegram_message(update):
    """
    Procesa los mensajes recibidos en Telegram y responde según la consulta:
      - Si se solicita un gráfico, llama a PrintGraphic.
      - Si se solicita "indicadores" o se menciona "bnb", responde con los indicadores técnicos actuales.
      - Si se menciona "dominancia" o "btc", utiliza OpenAI para generar un análisis descriptivo de la situación de BTC.
      - En otros casos, se utiliza OpenAI para responder de forma general basada en los indicadores.
    Solo procesa mensajes nuevos (con fecha posterior a START_TIME).
    """
    message_obj = update.get("message", {})
    message_text = message_obj.get("text", "").strip()
    chat_id = message_obj.get("chat", {}).get("id")
    user_data = message_obj.get("from", {})
    username = user_data.get("username") or user_data.get("first_name", "Agente")
    message_date = message_obj.get("date", 0)

    # Ignorar mensajes antiguos o sin texto/ID
    if message_date < START_TIME or not message_text or not chat_id:
        return

    lower_msg = message_text.lower()

    # Rama: Solicitud de gráfico
    if any(phrase in lower_msg for phrase in ["grafico", "gráfico"]):
        try:
            from PrintGraphic import send_graphic, extract_timeframe
            timeframe_req = extract_timeframe(lower_msg)
            chart_type = "line"
            if any(keyword in lower_msg for keyword in ["vela", "velas", "candlestick", "japonesas"]):
                chart_type = "candlestick"
            send_graphic(chat_id, timeframe_req, chart_type)
        except Exception as e:
            send_telegram_message(f"Error al generar gráfico: {e}", chat_id)
            print(f"[Error] Generando gráfico: {e}")
        return

    # Rama: Solicitud de indicadores técnicos para BNB
    if "indicador" in lower_msg or "bnb" in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            custom_signal = aggregate_signals(data)
            if not custom_signal:
                custom_signal = "No se detectaron señales técnicas relevantes en este momento."
            personalized_msg = (
                f"Hola agente @{username}, estos son los indicadores técnicos actuales para {SYMBOL}:\n\n{custom_signal}"
            )
            send_telegram_message(personalized_msg, chat_id)
        except Exception as e:
            send_telegram_message(f"Error al obtener indicadores: {e}", chat_id)
            print(f"[Error] Indicadores: {e}")
        return

    # Rama: Solicitud de análisis sobre dominancia/BTC
    if "dominancia" in lower_msg or "btc" in lower_msg:
        try:
            btc_price = fetch_btc_price()
            btc_dominance = fetch_btc_dominance()
            # Construir prompt para análisis descriptivo de BTC
            context = (
                f"El precio actual de BTC es ${btc_price:.2f} y la dominancia es de {btc_dominance:.2f}%. "
                "Analiza de forma concisa y descriptiva qué implica esta situación para el mercado, especialmente para las altcoins."
            )
            system_prompt = (
                "Eres un analista financiero experto, responde de forma precisa, en español, y proporciona insights relevantes."
            )
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context}
                ],
                max_tokens=500,
                temperature=0.7
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            answer = f"⚠️ Error al procesar el análisis de dominancia: {e}"
            print(f"[Error] Dominancia: {e}")
        send_telegram_message(answer, chat_id)
        return

    # Rama: Consulta general a OpenAI
    try:
        language = detect_language(message_text)
    except Exception as e:
        language = 'en'
        print(f"[Error] detect_language: {e}")

    try:
        data = fetch_data(SYMBOL, TIMEFRAME)
        indicators = calculate_indicators(data)
    except Exception as e:
        send_telegram_message(f"Error al obtener datos técnicos: {e}", chat_id)
        print(f"[Error] Obteniendo datos técnicos: {e}")
        return

    if language == 'es':
        system_prompt = (
            "Eres Higgs X, el agente de inteligencia del escuadrón encargado de vigilar el ecosistema de Virtuals. "
            "Cuando respondas, preséntate siempre como 'Higgs X' y dirige tus mensajes al usuario utilizando su nombre, "
            "por ejemplo, 'agente @mrtrompet'. Responde de forma concisa, seria y con un toque de misterio."
        )
        context = (
            f"Hola agente @{username}, aquí Higgs X al habla. Mi misión es vigilar el ecosistema de Virtuals, "
            "rastrear a las ballenas y mantener informado al escuadrón sobre cada fluctuación del mercado en tiempo real.\n\n"
            f"Indicadores técnicos actuales para {SYMBOL}:\n"
            f"- Precio: ${indicators['price']:.2f}\n"
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
    else:
        system_prompt = (
            "You are Higgs X, the intelligence agent responsible for monitoring the Binance ecosystem. "
            "When you respond, always introduce yourself as 'Higgs X' and address the user using their name, "
            "for example, 'agent @mrtrompet'. Respond concisely and with a touch of mystery."
        )
        context = (
            f"Hello agent @{username}, this is Higgs X speaking. My mission is to monitor the Virtuals ecosystem, "
            "track the whales, and keep the squad informed about every market fluctuation in real time.\n\n"
            f"Updated technical indicators for {SYMBOL}:\n"
            f"- Price: ${indicators['price']:.2f}\n"
            f"- RSI: {indicators['rsi']:.2f}\n"
            f"- MACD: {indicators['macd']:.2f} (Signal: {indicators['macd_signal']:.2f})\n"
            f"- SMA10: {indicators['sma_10']:.2f} | SMA25: {indicators['sma_25']:.2f} | SMA50: {indicators['sma_50']:.2f}\n"
            f"- Volume: {indicators['volume_level']} (CMF: {indicators['cmf']:.2f})\n\n"
            "Bollinger Bands:\n"
            f"Low: ${indicators['bb_low']:.2f}\n"
            f"Medium: ${indicators['bb_medium']:.2f}\n"
            f"High: ${indicators['bb_high']:.2f}\n\n"
            f"Question: {message_text}"
        )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            max_tokens=500,
            temperature=0.7
        )
        answer = response.choices[0].message.content.strip()
        # Escapar manualmente caracteres problemáticos
        answer = answer.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
    except Exception as e:
        answer = f"⚠️ Error al procesar la solicitud: {e}"
        print(f"[Error] OpenAI: {e}")

    send_telegram_message(answer, chat_id)

def get_updates():
    """Obtiene los últimos mensajes enviados al bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            updates = response.json().get("result", [])
            return [upd for upd in updates if upd.get("message", {}).get("date", 0) >= START_TIME]
        else:
            print(f"[Error] Al obtener actualizaciones: {response.text}")
            return []
    except Exception as e:
        print(f"[Error] En la conexión con Telegram: {e}")
        return []
