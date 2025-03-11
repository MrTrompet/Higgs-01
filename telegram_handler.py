import requests
import openai
import time
from langdetect import detect
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, OPENAI_API_KEY, SYMBOL, TIMEFRAME
from market import fetch_historical_data
from indicators import calculate_indicators_for_bnb, check_cross_signals
from btc_indicators import get_btc_indicators
from ml_model import aggregate_signals

# Configurar API key de OpenAI
openai.api_key = OPENAI_API_KEY
if not openai.api_key:
    print("[DEBUG] ¡Atención! La API key de OpenAI no está configurada correctamente.")

# Variables globales para el historial de conversación y solicitudes pendientes
conversation_history = {}  # Estructura: { chat_id: {"messages": [...], "context": {...} } }
pending_requests = {}

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
    """Forzamos siempre el español."""
    return 'es'

def detectar_activo(mensaje, contexto=None):
    """
    Detecta el activo (BNB o BTC) a partir del mensaje o del contexto.
    Si no se identifica, devuelve None.
    """
    mensaje = mensaje.lower()
    if "btc" in mensaje:
        return "BTC"
    elif "bnb" in mensaje:
        return "BNB"
    elif contexto and "activo" in contexto:
        return contexto["activo"]
    else:
        return None

def handle_telegram_message(update):
    """
    Procesa los mensajes recibidos en Telegram y responde según el contenido.
    Se delega la obtención de indicadores a funciones especializadas:
      - Para BNB: calculate_indicators_for_bnb() (en indicators.py).
      - Para BTC: get_btc_indicators() (en btc_indicators.py).
    Además, se detecta el activo solicitado y se actualiza el contexto.
    """
    global conversation_history, pending_requests

    print(f"[DEBUG] Update recibido: {update}")
    message_obj = update.get("message", {})
    message_text = message_obj.get("text", "").strip()
    chat_id = message_obj.get("chat", {}).get("id")
    user_data = message_obj.get("from", {})
    username = user_data.get("username") or user_data.get("first_name", "Agente")

    if not message_text or not chat_id:
        print("[DEBUG] Mensaje vacío o sin chat_id, se descarta.")
        return

    lower_msg = message_text.lower()
    print(f"[DEBUG] Procesando mensaje de @{username}: {message_text}")

    # Si existe una solicitud pendiente para seleccionar activo, se procesa inmediatamente.
    if chat_id in pending_requests and pending_requests[chat_id] == "seleccionar_activo":
        activo_response = message_text.strip().upper()
        if activo_response in ["BNB", "BTC"]:
            conversation_history.setdefault(chat_id, {"messages": [], "context": {}})["context"]["activo"] = activo_response
            send_telegram_message(f"Activo actualizado a {activo_response}.", chat_id)
            del pending_requests[chat_id]
            return
        else:
            send_telegram_message("Activo no reconocido. Por favor, responde con BNB o BTC.", chat_id)
            return

    # Actualizar historial de conversación
    if chat_id not in conversation_history:
        conversation_history[chat_id] = {"messages": [], "context": {}}
    conversation_history[chat_id]["messages"].append({"role": "user", "content": message_text})

    # Rama: Respuesta rápida a saludos sencillos
    greetings = ["hola", "que onda", "buenos", "saludos"]
    if lower_msg in greetings:
        send_telegram_message("¡Hola! Estoy en la blockchain analizando el mercado, listo para ayudarte.", chat_id)
        return

    # Rama: Si el mensaje contiene "dominancia", se responde con análisis de BTC
    if "dominancia" in lower_msg:
        try:
            btc_indicators = get_btc_indicators()
            btc_price = btc_indicators['price']
            btc_dominance = btc_indicators['dominance']
            answer = (f"Actualmente, BTC se cotiza a ${btc_price:.2f} y su dominancia es de {btc_dominance:.2f}%.\n"
                      "Recuerda: Si la dominancia aumenta mientras el precio cae, podría indicar señales de manipulación.")
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id]["messages"].append({"role": "assistant", "content": answer})
        except Exception as e:
            send_telegram_message(f"Error al obtener la dominancia: {e}", chat_id)
        return

    # Detectar activo usando el mensaje y/o el contexto almacenado
    activo = detectar_activo(message_text, conversation_history[chat_id].get("context"))
    if not activo:
        send_telegram_message("¿Deseas la actualización de BNB o BTC?", chat_id)
        pending_requests[chat_id] = "seleccionar_activo"
        return
    else:
        conversation_history[chat_id]["context"]["activo"] = activo

    # Rama: Consulta de precio
    if "precio" in lower_msg:
        try:
            if activo == "BNB":
                indicators = calculate_indicators_for_bnb()
                answer = f"El precio actual de BNB es: ${indicators['price']:.2f}"
            elif activo == "BTC":
                btc_indicators = get_btc_indicators()
                answer = f"El precio actual de BTC es: ${btc_indicators['price']:.2f}"
            else:
                answer = "Activo no reconocido para consulta de precio."
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id]["messages"].append({"role": "assistant", "content": answer})
        except Exception as e:
            send_telegram_message(f"Error al obtener el precio: {e}", chat_id)
        return

    # Rama: Consulta compleja o actualización (análisis, estrategia, indicadores)
    if any(keyword in lower_msg for keyword in ["analiza", "análisis", "analisis", "compara", "estrategia", "actualizacion", "actualización", "indicadores"]):
        try:
            if activo == "BNB":
                indicators = calculate_indicators_for_bnb()
            elif activo == "BTC":
                indicators = get_btc_indicators()
            else:
                raise Exception("Activo no soportado.")
        except Exception as e:
            fallback_context = ("No se pudieron obtener datos técnicos en tiempo real. "
                                "Revisa una plataforma de trading para obtener información actualizada.")
            send_telegram_message(fallback_context, chat_id)
            return

        system_prompt = (
            "Eres Higgs, Agente X. Tienes acceso a datos técnicos actualizados y a la memoria de la conversación. "
            "Responde de forma concisa, seria y con un toque de misterio, siempre en español. "
            "Utiliza los siguientes indicadores para generar un análisis robusto."
        )
        context_text = (
            f"Indicadores técnicos actuales para {activo}:\n"
            f"• Precio: ${indicators['price']:.2f}\n"
            f"• RSI: {indicators['rsi']:.2f}\n"
            f"• MACD: {indicators['macd']:.2f} (Señal: {indicators['macd_signal']:.2f})\n"
            f"• SMA10: {indicators['sma_10']:.2f} | SMA25: {indicators['sma_25']:.2f} | SMA50: {indicators['sma_50']:.2f}\n"
            f"• Bollinger Bands: Bajo ${indicators['bb_low']:.2f}, Medio ${indicators['bb_medium']:.2f}, Alto ${indicators['bb_high']:.2f}\n\n"
            f"Pregunta: {message_text}"
        )
        messages = [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": context_text}]
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            answer = response.choices[0].message.content.strip()
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id]["messages"].append({"role": "assistant", "content": answer})
        except Exception as e:
            error_msg = f"⚠️ Error al procesar la solicitud: {e}"
            send_telegram_message(error_msg, chat_id)
        return

    # Rama: Consultas específicas (ej. RSI, MACD, SMA, CMF)
    if "rsi" in lower_msg and "indicador" not in lower_msg:
        try:
            if activo == "BNB":
                indicators = calculate_indicators_for_bnb()
                answer = f"El RSI actual para BNB es: {indicators['rsi']:.2f}"
            elif activo == "BTC":
                btc_indicators = get_btc_indicators()
                answer = f"El RSI actual para BTC es: {btc_indicators['rsi']:.2f}"
            else:
                answer = "Activo no reconocido."
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id]["messages"].append({"role": "assistant", "content": answer})
        except Exception as e:
            send_telegram_message(f"Error al obtener el RSI: {e}", chat_id)
        return

    if "macd" in lower_msg:
        try:
            if activo == "BNB":
                indicators = calculate_indicators_for_bnb()
                answer = f"El MACD actual para BNB es: {indicators['macd']:.2f} (Señal: {indicators['macd_signal']:.2f})"
            elif activo == "BTC":
                btc_indicators = get_btc_indicators()
                answer = f"El MACD actual para BTC es: {btc_indicators['macd']:.2f} (Señal: {btc_indicators['macd_signal']:.2f})"
            else:
                answer = "Activo no reconocido."
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id]["messages"].append({"role": "assistant", "content": answer})
        except Exception as e:
            send_telegram_message(f"Error al obtener el MACD: {e}", chat_id)
        return

    if "sma" in lower_msg:
        try:
            if activo == "BNB":
                indicators = calculate_indicators_for_bnb()
                answer = (
                    f"Valores SMA para BNB:\n"
                    f"• SMA10: {indicators['sma_10']:.2f}\n"
                    f"• SMA25: {indicators['sma_25']:.2f}\n"
                    f"• SMA50: {indicators['sma_50']:.2f}"
                )
            elif activo == "BTC":
                btc_indicators = get_btc_indicators()
                answer = (
                    f"Valores SMA para BTC:\n"
                    f"• SMA10: {btc_indicators['sma_10']:.2f}\n"
                    f"• SMA25: {btc_indicators['sma_25']:.2f}\n"
                    f"• SMA50: {btc_indicators['sma_50']:.2f}"
                )
            else:
                answer = "Activo no reconocido."
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id]["messages"].append({"role": "assistant", "content": answer})
        except Exception as e:
            send_telegram_message(f"Error al obtener las SMA: {e}", chat_id)
        return

    if "cmf" in lower_msg:
        try:
            if activo == "BNB":
                indicators = calculate_indicators_for_bnb()
                answer = f"El CMF para BNB es: {indicators['cmf']:.2f}"
            elif activo == "BTC":
                btc_indicators = get_btc_indicators()
                answer = f"El CMF para BTC es: {btc_indicators['cmf']:.2f}"
            else:
                answer = "Activo no reconocido."
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id]["messages"].append({"role": "assistant", "content": answer})
        except Exception as e:
            send_telegram_message(f"Error al obtener el CMF: {e}", chat_id)
        return

    # Fallback: Si la consulta no coincide con ninguna rama, se solicita mayor especificidad.
    try:
        fallback_message = "No entendí tu solicitud. Por favor, sé más específico en tu consulta."
        send_telegram_message(fallback_message, chat_id)
    except Exception as e:
        print(f"[Error] Fallback: {e}")

def analyze_sma_crosses(df):
    """
    Analiza cruces de SMA (por ejemplo, entre SMA10 y SMA25) en datos históricos.
    Retorna una cadena con el análisis.
    """
    if df.empty or len(df) < 25:
        return "Datos insuficientes para analizar cruces."
    df = df.copy()
    df['sma_10'] = df['close'].rolling(window=10).mean()
    df['sma_25'] = df['close'].rolling(window=25).mean()
    last = df.iloc[-1]
    prev = df.iloc[-2]
    if prev['sma_10'] > prev['sma_25'] and last['sma_10'] < last['sma_25']:
        return f"Se detectó un cruce bajista entre SMA10 y SMA25 el {last['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}."
    elif prev['sma_10'] < prev['sma_25'] and last['sma_10'] > last['sma_25']:
        return f"Se detectó un cruce alcista entre SMA10 y SMA25 el {last['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}."
    else:
        return "No se detectaron cruces significativos recientes entre SMA10 y SMA25."

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
