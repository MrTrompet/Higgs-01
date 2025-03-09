import requests
import openai
import time
from langdetect import detect
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, OPENAI_API_KEY, SYMBOL, TIMEFRAME
from market import fetch_data, fetch_btc_price
from indicators import calculate_indicators, fetch_btc_dominance
from ml_model import aggregate_signals

# Configurar API key de OpenAI
openai.api_key = OPENAI_API_KEY
if not openai.api_key:
    print("[DEBUG] ¡Atención! La API key de OpenAI no está configurada correctamente.")

START_TIME = 0  # Procesamos todos los mensajes para pruebas

def send_telegram_message(message, chat_id=None):
    """Envía un mensaje al chat de Telegram."""
    if not chat_id:
        chat_id = TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"[Error] Al enviar mensaje a Telegram: {response.text}")
    except Exception as e:
        print(f"[Error] En la conexión con Telegram: {e}")

def detect_language(text):
    """Detecta el idioma usando langdetect."""
    try:
        lang = detect(text)
        return 'es' if lang == 'es' else 'en'
    except Exception as e:
        print(f"[Error] detect_language: {e}")
        return 'en'

def handle_telegram_message(update):
    """
    Procesa los mensajes recibidos en Telegram y responde según el contenido:
      - "grafico": llama a PrintGraphic.
      - "precio" + "bnb": responde con el precio actual de SYMBOL.
      - Si el mensaje contiene "todos" y "indicador" o "indicadores técnicos" o "completo", envía un reporte completo.
      - Si se menciona individualmente "rsi", "adx", "macd", "sma" o "cmf", responde con ese valor.
      - "dominancia" o "btc": usa OpenAI para un análisis descriptivo sobre BTC.
      - En otro caso, envía una consulta general a OpenAI.
    """
    print(f"[DEBUG] Update recibido: {update}")
    message_obj = update.get("message", {})
    message_text = message_obj.get("text", "").strip()
    chat_id = message_obj.get("chat", {}).get("id")
    user_data = message_obj.get("from", {})
    username = user_data.get("username") or user_data.get("first_name", "Agente")
    message_date = message_obj.get("date", 0)
    
    if not message_text or not chat_id:
        print("[DEBUG] Mensaje vacío o sin chat_id, se descarta.")
        return

    lower_msg = message_text.lower()
    print(f"[DEBUG] Procesando mensaje de @{username}: {message_text}")

    # Rama: Solicitud de gráfico
    if any(phrase in lower_msg for phrase in ["grafico", "gráfico"]):
        try:
            from PrintGraphic import send_graphic, extract_timeframe
            timeframe_req = extract_timeframe(lower_msg)
            chart_type = "line"
            if any(keyword in lower_msg for keyword in ["vela", "velas", "candlestick", "japonesas"]):
                chart_type = "candlestick"
            print(f"[DEBUG] Solicitado gráfico: {chart_type} en {timeframe_req}")
            send_graphic(chat_id, timeframe_req, chart_type)
        except Exception as e:
            send_telegram_message(f"Error al generar gráfico: {e}", chat_id)
            print(f"[Error] Generando gráfico: {e}")
        return

    # Rama: Solicitud de precio actual de BNB
    if "precio" in lower_msg and "bnb" in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            price = indicators.get('price', None)
            if price is not None:
                send_telegram_message(f"El precio actual de {SYMBOL} es: ${price:.2f}", chat_id)
                print(f"[DEBUG] Precio enviado: ${price:.2f}")
            else:
                send_telegram_message("No se pudo determinar el precio actual.", chat_id)
        except Exception as e:
            send_telegram_message(f"Error al obtener el precio: {e}", chat_id)
            print(f"[Error] Precio: {e}")
        return

    # Rama: Solicitud de reporte completo de indicadores técnicos
    if ("todos" in lower_msg and "indicador" in lower_msg) or ("indicadores" in lower_msg and ("técnicos" in lower_msg or "completos" in lower_msg)):
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            message = (
                f"Hola agente @{username}, aquí tienes el reporte completo de indicadores técnicos para {SYMBOL}:\n\n"
                f"Precio: ${indicators['price']:.2f}\n"
                f"RSI: {indicators['rsi']:.2f}\n"
                f"ADX: {indicators['adx']:.2f}\n"
                f"MACD: {indicators['macd']:.2f} (Señal: {indicators['macd_signal']:.2f})\n"
                f"SMA10: {indicators['sma_10']:.2f} | SMA25: {indicators['sma_25']:.2f} | SMA50: {indicators['sma_50']:.2f}\n"
                f"CMF: {indicators['cmf']:.2f}\n"
                f"Bollinger Bands: Low ${indicators['bb_low']:.2f}, Medium ${indicators['bb_medium']:.2f}, High ${indicators['bb_high']:.2f}\n"
            )
            send_telegram_message(message, chat_id)
            print("[DEBUG] Reporte completo enviado.")
        except Exception as e:
            send_telegram_message(f"Error al obtener el reporte completo de indicadores: {e}", chat_id)
            print(f"[Error] Reporte completo: {e}")
        return

    # Rama: Solicitudes individuales de indicadores
    if "rsi" in lower_msg and "indicador" not in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            send_telegram_message(f"El RSI actual para {SYMBOL} es: {indicators['rsi']:.2f}", chat_id)
            print(f"[DEBUG] RSI enviado: {indicators['rsi']:.2f}")
        except Exception as e:
            send_telegram_message(f"Error al obtener el RSI: {e}", chat_id)
            print(f"[Error] RSI: {e}")
        return

    if "adx" in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            send_telegram_message(f"El ADX actual para {SYMBOL} es: {indicators['adx']:.2f}", chat_id)
            print(f"[DEBUG] ADX enviado: {indicators['adx']:.2f}")
        except Exception as e:
            send_telegram_message(f"Error al obtener el ADX: {e}", chat_id)
            print(f"[Error] ADX: {e}")
        return

    if "macd" in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            send_telegram_message(f"El MACD actual para {SYMBOL} es: {indicators['macd']:.2f} (Señal: {indicators['macd_signal']:.2f})", chat_id)
            print(f"[DEBUG] MACD enviado: {indicators['macd']:.2f}")
        except Exception as e:
            send_telegram_message(f"Error al obtener el MACD: {e}", chat_id)
            print(f"[Error] MACD: {e}")
        return

    if "sma" in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            message = (f"Valores SMA para {SYMBOL}:\n"
                       f"SMA10: {indicators['sma_10']:.2f}\n"
                       f"SMA25: {indicators['sma_25']:.2f}\n"
                       f"SMA50: {indicators['sma_50']:.2f}")
            send_telegram_message(message, chat_id)
            print(f"[DEBUG] SMA enviados.")
        except Exception as e:
            send_telegram_message(f"Error al obtener las SMA: {e}", chat_id)
            print(f"[Error] SMA: {e}")
        return

    if "cmf" in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            send_telegram_message(f"El CMF para {SYMBOL} es: {indicators['cmf']:.2f}", chat_id)
            print(f"[DEBUG] CMF enviado: {indicators['cmf']:.2f}")
        except Exception as e:
            send_telegram_message(f"Error al obtener el CMF: {e}", chat_id)
            print(f"[Error] CMF: {e}")
        return

    # Rama: Solicitud de análisis sobre dominancia/BTC
    if "dominancia" in lower_msg or "btc" in lower_msg:
        try:
            try:
                btc_price = fetch_btc_price()
            except Exception as e:
                print(f"[Error] fetch_btc_price: {e}")
                btc_price = None
            try:
                btc_dominance = fetch_btc_dominance()
            except Exception as e:
                print(f"[Error] fetch_btc_dominance: {e}")
                btc_dominance = None
            if btc_price is None or btc_dominance is None:
                answer = "No se pudo obtener la información de BTC en este momento."
            else:
                context = (f"El precio actual de BTC es ${btc_price:.2f} y su dominancia es del {btc_dominance:.2f}%. "
                           "Analiza detalladamente esta situación, detecta posibles manipulaciones y evalúa oportunidades de entrada en corto para altcoins.")
                system_prompt = ("Eres un analista financiero experto. Interpreta la situación del mercado de criptomonedas y proporciona insights precisos en español.")
                print(f"[DEBUG] Análisis dominancia: BTC ${btc_price:.2f}, Dominancia {btc_dominance:.2f}%")
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
                print(f"[DEBUG] Respuesta OpenAI (dominancia): {answer}")
        except Exception as e:
            answer = f"⚠️ Error al procesar el análisis de dominancia: {e}"
            print(f"[Error] Dominancia: {e}")
        send_telegram_message(answer, chat_id)
        return

    # Rama: Consulta general a OpenAI para otros mensajes (por ejemplo, "hola", "/start", etc.)
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
            "Eres Higgs X, el agente de inteligencia encargado de vigilar el ecosistema de Virtuals. "
            "Cuando respondas, preséntate como 'Higgs X' y utiliza un tono conciso, serio y misterioso."
        )
        context = (
            f"Hola agente @{username}, aquí Higgs X al habla. Mi misión es vigilar el ecosistema de Virtuals.\n\n"
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
            "Respond concisely and with a touch of mystery, addressing the user by name."
        )
        context = (
            f"Hello agent @{username}, this is Higgs X speaking. My mission is to monitor the Virtuals ecosystem.\n\n"
            f"Technical indicators for {SYMBOL}:\n"
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
        print("[DEBUG] Enviando consulta general a OpenAI...")
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
        answer = answer.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
        print(f"[DEBUG] Respuesta OpenAI general: {answer}")
    except Exception as e:
        answer = f"⚠️ Error al procesar la solicitud: {e}"
        print(f"[Error] OpenAI: {e}")

    send_telegram_message(answer, chat_id)

def get_updates(offset=None):
    """Obtiene las actualizaciones desde Telegram usando el parámetro offset."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {}
    if offset is not None:
        params["offset"] = offset
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            updates = response.json().get("result", [])
            return updates
        else:
            print(f"[Error] Al obtener actualizaciones: {response.text}")
            return []
    except Exception as e:
        print(f"[Error] En la conexión con Telegram: {e}")
        return []
