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
    """Detecta el idioma usando langdetect (se espera español)."""
    try:
        lang = detect(text)
        return 'es'  # Forzamos el español
    except Exception as e:
        print(f"[Error] detect_language: {e}")
        return 'es'

def handle_telegram_message(update):
    """
    Procesa los mensajes recibidos en Telegram y responde en español según el contenido:
      - Si se solicita "gráfico", llama a PrintGraphic.
      - Si se pide "precio" de BNB o BTC, responde con el precio actual.
      - Si se solicita "todos los indicadores", "indicadores técnicos completos" o "actualización", envía un reporte completo.
      - Si se solicitan indicadores individuales (RSI, ADX, MACD, SMA, CMF), responde solo con ese valor.
      - Si se consulta la dominancia o BTC, usa OpenAI para generar un análisis breve y enfocado.
      - En otro caso, realiza una consulta general a OpenAI.
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
    if "grafico" in lower_msg or "gráfico" in lower_msg:
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

    # Rama: Solicitud de precio
    if "precio" in lower_msg:
        if "bnb" in lower_msg:
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
        if "btc" in lower_msg:
            try:
                btc_price = fetch_btc_price()
                send_telegram_message(f"El precio actual de BTC es: ${btc_price:.2f}", chat_id)
                print(f"[DEBUG] BTC Precio enviado: ${btc_price:.2f}")
            except Exception as e:
                send_telegram_message(f"Error al obtener el precio de BTC: {e}", chat_id)
                print(f"[Error] BTC Precio: {e}")
            return

    # Rama: Solicitud de reporte completo de indicadores técnicos
    if ("todos" in lower_msg and "indicador" in lower_msg) or ("indicadores" in lower_msg and ("técnicos" in lower_msg or "completos" in lower_msg or "actualización" in lower_msg)):
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            message = (
                f"Saludos, soy Higgs, Agente X.\n\n"
                f"Reporte completo de indicadores para {SYMBOL}:\n"
                f"• Precio: ${indicators['price']:.2f}\n"
                f"• RSI: {indicators['rsi']:.2f}\n"
                f"• ADX: {indicators['adx']:.2f}\n"
                f"• MACD: {indicators['macd']:.2f} (Señal: {indicators['macd_signal']:.2f})\n"
                f"• SMA10: {indicators['sma_10']:.2f} | SMA25: {indicators['sma_25']:.2f} | SMA50: {indicators['sma_50']:.2f}\n"
                f"• CMF: {indicators['cmf']:.2f}\n"
                f"• Bollinger Bands: Bajo ${indicators['bb_low']:.2f}, Medio ${indicators['bb_medium']:.2f}, Alto ${indicators['bb_high']:.2f}\n"
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
            message = (
                f"Valores SMA para {SYMBOL}:\n"
                f"• SMA10: {indicators['sma_10']:.2f}\n"
                f"• SMA25: {indicators['sma_25']:.2f}\n"
                f"• SMA50: {indicators['sma_50']:.2f}"
            )
            send_telegram_message(message, chat_id)
            print("[DEBUG] SMA enviados.")
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

    # Rama: Solicitud de análisis de dominancia/BTC
    if "dominancia" in lower_msg or ("btc" in lower_msg and "precio" not in lower_msg):
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
                # Se calcula la diferencia porcentual entre el cambio de precio y el cambio de dominancia
                context = (f"BTC: precio ${btc_price:.2f}, dominancia {btc_dominance:.2f}%. "
                           "Interpreta de forma precisa la relación entre el precio y la dominancia, "
                           "y evalúa si se observa una situación inusual que sugiera manipulación, "
                           "para sugerir una posible entrada en corto para altcoins.")
                system_prompt = ("Eres un analista financiero experto. Proporciona un análisis conciso en español basado en la relación entre el precio de BTC y su dominancia.")
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

    # Rama: Consulta general a OpenAI para otros mensajes (ej. "hola", "/start", etc.)
    try:
        language = detect_language(message_text)
    except Exception as e:
        language = 'es'
        print(f"[Error] detect_language: {e}")
    
    try:
        data = fetch_data(SYMBOL, TIMEFRAME)
        indicators = calculate_indicators(data)
    except Exception as e:
        send_telegram_message(f"Error al obtener datos técnicos: {e}", chat_id)
        print(f"[Error] Obteniendo datos técnicos: {e}")
        return

    system_prompt = (
        "Eres Higgs, Agente X. Hace años me introdujeron en la cadena de bloques con un propósito: infiltrarme en este vasto ecosistema, rastrear los movimientos de las ballenas y brindar información en tiempo real. "
        "Responde de forma concisa, seria y con un toque de misterio, siempre en español."
    )
    context = (
        f"Hola agente @{username}, aquí Higgs, Agente X, a tu servicio.\n\n"
        f"Indicadores técnicos actuales para {SYMBOL}:\n"
        f"• Precio: ${indicators['price']:.2f}\n"
        f"• RSI: {indicators['rsi']:.2f}\n"
        f"• MACD: {indicators['macd']:.2f} (Señal: {indicators['macd_signal']:.2f})\n"
        f"• SMA10: {indicators['sma_10']:.2f} | SMA25: {indicators['sma_25']:.2f} | SMA50: {indicators['sma_50']:.2f}\n"
        f"• Volumen: {indicators['volume_level']} (CMF: {indicators['cmf']:.2f})\n"
        f"• Bollinger Bands: Bajo ${indicators['bb_low']:.2f}, Medio ${indicators['bb_medium']:.2f}, Alto ${indicators['bb_high']:.2f}\n\n"
        f"Pregunta: {message_text}"
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
        # Escapar caracteres problemáticos
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
