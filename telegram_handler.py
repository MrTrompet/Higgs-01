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

# Variable global para almacenar el historial de cada chat (simulando memoria)
conversation_history = {}

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

def handle_telegram_message(update):
    """
    Procesa los mensajes recibidos en Telegram y responde en español según el contenido.
    
    Mejoras aplicadas:
    - Se reordenan y combinan condiciones para interpretar correctamente consultas que incluyan
      múltiples palabras clave (por ejemplo, "precio" + "análisis" o "indicadores").
    - Se agrega almacenamiento de historial por chat para mantener el contexto de la conversación.
    - Se incluye una rama específica para comparar BTC (precio y dominancia).
    """
    global conversation_history

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

    # Actualizar historial de conversación por chat
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    conversation_history[chat_id].append({"role": "user", "content": message_text})

    # Rama 1: Solicitud de gráfico (prioridad alta)
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

    # Rama 2: Consultas complejas (análisis, comparaciones o estrategia)
    if any(keyword in lower_msg for keyword in ["analiza", "análisis", "analisis", "compara", "estrategia", "entrada", "puntos de entrada"]):
        # Caso especial: comparación de BTC (precio y dominancia)
        if "btc" in lower_msg and "dominancia" in lower_msg:
            try:
                btc_price = fetch_btc_price()
                btc_dominance = fetch_btc_dominance()
                answer = f"Comparación BTC:\n• Precio: ${btc_price:.2f}\n• Dominancia: {btc_dominance:.2f}%\n"
                if "1h" in lower_msg:
                    answer += ("Análisis en 1h: Si BTC baja y la dominancia aumenta, "
                               "podría tratarse de una señal de acumulación o manipulación. Mantente alerta.")
                else:
                    answer += ("Esta comparación indica la distribución actual del mercado: "
                               "una alta dominancia aun cuando el precio fluctúa puede reflejar movimientos relativos de altcoins.")
                send_telegram_message(answer, chat_id)
                conversation_history[chat_id].append({"role": "assistant", "content": answer})
            except Exception as e:
                send_telegram_message(f"Error al obtener datos de BTC: {e}", chat_id)
                print(f"[Error] BTC Dominancia/Precio: {e}")
            return

        # En otras consultas complejas se construye un contexto completo y se consulta a OpenAI.
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
        except Exception as e:
            fallback_context = ("No se pudieron obtener datos técnicos en tiempo real. "
                                "Revisa una plataforma de trading para obtener información actualizada.")
            send_telegram_message(fallback_context, chat_id)
            print(f"[Error] Datos técnicos: {e}")
            return

        system_prompt = (
            "Eres Higgs, Agente X. Tienes acceso a los datos técnicos actuales del mercado y a la memoria de la conversación. "
            "Responde de forma concisa, seria y con un toque de misterio, siempre en español. "
            "Tu respuesta debe integrar los datos actuales (precio, RSI, MACD, SMA, Bollinger Bands, etc.) y dar un análisis coherente."
        )
        # Incluir el historial reciente (se puede limitar a los últimos 6 mensajes para no sobrepasar el límite)
        recent_history = conversation_history[chat_id][-6:]
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(recent_history)
        # Agregar el contexto técnico actual
        context = (
            f"Indicadores técnicos actuales para {SYMBOL}:\n"
            f"• Precio: ${indicators['price']:.2f}\n"
            f"• RSI: {indicators['rsi']:.2f}\n"
            f"• MACD: {indicators['macd']:.2f} (Señal: {indicators['macd_signal']:.2f})\n"
            f"• SMA10: {indicators['sma_10']:.2f} | SMA25: {indicators['sma_25']:.2f} | SMA50: {indicators['sma_50']:.2f}\n"
            f"• Volumen/CMF: {indicators.get('volume_level', 'N/A')} (CMF: {indicators['cmf']:.2f})\n"
            f"• Bollinger Bands: Bajo ${indicators['bb_low']:.2f}, Medio ${indicators['bb_medium']:.2f}, Alto ${indicators['bb_high']:.2f}\n\n"
            f"Pregunta: {message_text}"
        )
        messages.append({"role": "user", "content": context})
        try:
            print("[DEBUG] Enviando consulta compleja a OpenAI...")
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            answer = response.choices[0].message.content.strip()
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id].append({"role": "assistant", "content": answer})
            print(f"[DEBUG] Respuesta OpenAI compleja: {answer}")
        except Exception as e:
            error_msg = f"⚠️ Error al procesar la solicitud: {e}"
            send_telegram_message(error_msg, chat_id)
            print(f"[Error] OpenAI: {e}")
        return

    # Rama 3: Consultas simples de precio
    if "precio" in lower_msg:
        # Si la consulta es únicamente "precio" y menciona "bnb" o el símbolo, se envía solo el precio.
        if "bnb" in lower_msg or SYMBOL.lower() in lower_msg:
            try:
                data = fetch_data(SYMBOL, TIMEFRAME)
                indicators = calculate_indicators(data)
                answer = f"El precio actual de {SYMBOL} es: ${indicators['price']:.2f}"
                send_telegram_message(answer, chat_id)
                conversation_history[chat_id].append({"role": "assistant", "content": answer})
                print(f"[DEBUG] Precio enviado: ${indicators['price']:.2f}")
            except Exception as e:
                send_telegram_message(f"Error al obtener el precio: {e}", chat_id)
                print(f"[Error] Precio: {e}")
            return
        if "btc" in lower_msg:
            try:
                btc_price = fetch_btc_price()
                answer = f"El precio actual de BTC es: ${btc_price:.2f}"
                send_telegram_message(answer, chat_id)
                conversation_history[chat_id].append({"role": "assistant", "content": answer})
                print(f"[DEBUG] BTC Precio enviado: ${btc_price:.2f}")
            except Exception as e:
                send_telegram_message(f"Error al obtener el precio de BTC: {e}", chat_id)
                print(f"[Error] BTC Precio: {e}")
            return

    # Rama 4: Consultas específicas de indicadores individuales
    if "rsi" in lower_msg and "indicador" not in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            answer = f"El RSI actual para {SYMBOL} es: {indicators['rsi']:.2f}"
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id].append({"role": "assistant", "content": answer})
            print(f"[DEBUG] RSI enviado: {indicators['rsi']:.2f}")
        except Exception as e:
            send_telegram_message(f"Error al obtener el RSI: {e}", chat_id)
            print(f"[Error] RSI: {e}")
        return

    if "adx" in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            answer = f"El ADX actual para {SYMBOL} es: {indicators['adx']:.2f}"
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id].append({"role": "assistant", "content": answer})
            print(f"[DEBUG] ADX enviado: {indicators['adx']:.2f}")
        except Exception as e:
            send_telegram_message(f"Error al obtener el ADX: {e}", chat_id)
            print(f"[Error] ADX: {e}")
        return

    if "macd" in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            answer = f"El MACD actual para {SYMBOL} es: {indicators['macd']:.2f} (Señal: {indicators['macd_signal']:.2f})"
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id].append({"role": "assistant", "content": answer})
            print(f"[DEBUG] MACD enviado: {indicators['macd']:.2f}")
        except Exception as e:
            send_telegram_message(f"Error al obtener el MACD: {e}", chat_id)
            print(f"[Error] MACD: {e}")
        return

    if "sma" in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            answer = (
                f"Valores SMA para {SYMBOL}:\n"
                f"• SMA10: {indicators['sma_10']:.2f}\n"
                f"• SMA25: {indicators['sma_25']:.2f}\n"
                f"• SMA50: {indicators['sma_50']:.2f}"
            )
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id].append({"role": "assistant", "content": answer})
            print("[DEBUG] SMA enviados.")
        except Exception as e:
            send_telegram_message(f"Error al obtener las SMA: {e}", chat_id)
            print(f"[Error] SMA: {e}")
        return

    if "cmf" in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            answer = f"El CMF para {SYMBOL} es: {indicators['cmf']:.2f}"
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id].append({"role": "assistant", "content": answer})
            print(f"[DEBUG] CMF enviado: {indicators['cmf']:.2f}")
        except Exception as e:
            send_telegram_message(f"Error al obtener el CMF: {e}", chat_id)
            print(f"[Error] CMF: {e}")
        return

    # Rama 5: Consulta general o fallback a OpenAI para otros mensajes
    try:
        language = detect_language(message_text)
    except Exception as e:
        language = 'es'
        print(f"[Error] detect_language: {e}")

    # Intentar obtener datos técnicos; si falla, se envía un fallback
    try:
        data = fetch_data(SYMBOL, TIMEFRAME)
        indicators = calculate_indicators(data)
    except Exception as e:
        print(f"[Error] Obteniendo datos técnicos: {e}")
        fallback_context = (
            "No se pudieron obtener datos técnicos en tiempo real. "
            "Revisa una plataforma de trading para obtener la información actualizada."
        )
        send_telegram_message(fallback_context, chat_id)
        return

    system_prompt = (
        "Eres Higgs, Agente X. Tienes información actualizada del mercado y acceso a la memoria de la conversación. "
        "Responde de forma concisa, seria y con un toque de misterio, siempre en español."
    )
    # Se utiliza el historial completo (o los últimos mensajes) para mantener el contexto.
    recent_history = conversation_history[chat_id][-6:]
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(recent_history)
    context = (
        f"Indicadores técnicos actuales para {SYMBOL}:\n"
        f"• Precio: ${indicators['price']:.2f}\n"
        f"• RSI: {indicators['rsi']:.2f}\n"
        f"• MACD: {indicators['macd']:.2f} (Señal: {indicators['macd_signal']:.2f})\n"
        f"• SMA10: {indicators['sma_10']:.2f} | SMA25: {indicators['sma_25']:.2f} | SMA50: {indicators['sma_50']:.2f}\n"
        f"• Volumen/CMF: {indicators.get('volume_level', 'N/A')} (CMF: {indicators['cmf']:.2f})\n"
        f"• Bollinger Bands: Bajo ${indicators['bb_low']:.2f}, Medio ${indicators['bb_medium']:.2f}, Alto ${indicators['bb_high']:.2f}\n\n"
        f"Pregunta: {message_text}"
    )
    messages.append({"role": "user", "content": context})

    try:
        print("[DEBUG] Enviando consulta general a OpenAI...")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        answer = response.choices[0].message.content.strip()
        send_telegram_message(answer, chat_id)
        conversation_history[chat_id].append({"role": "assistant", "content": answer})
        print(f"[DEBUG] Respuesta OpenAI general: {answer}")
    except Exception as e:
        error_msg = f"⚠️ Error al procesar la solicitud: {e}"
        send_telegram_message(error_msg, chat_id)
        print(f"[Error] OpenAI: {e}")

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
