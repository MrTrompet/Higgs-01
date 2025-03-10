import requests
import openai
import time
from langdetect import detect
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, OPENAI_API_KEY, SYMBOL, TIMEFRAME
from market import fetch_data, fetch_btc_price, fetch_historical_data
from indicators import calculate_indicators, fetch_btc_dominance
from ml_model import aggregate_signals
import pandas as pd

# Configurar API key de OpenAI
openai.api_key = OPENAI_API_KEY
if not openai.api_key:
    print("[DEBUG] ¡Atención Agente! La API key de OpenAI no está configurada correctamente.")

START_TIME = 0  # Procesamos todos los mensajes para pruebas

# Variables globales para simular memoria y solicitudes pendientes
conversation_history = {}
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

def analyze_sma_crosses(df):
    """
    Analiza cruces de SMA (por ejemplo, entre SMA10 y SMA25) en datos históricos.
    Retorna una cadena con el análisis.
    """
    if df.empty or len(df) < 25:
        return "No tengo suficientes datos para analizar cruces."
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

def handle_telegram_message(update):
    """
    Procesa los mensajes recibidos en Telegram y responde en español según el contenido.
    
    Mejoras:
      - Se reordenan los bloques para que consultas simples (ej. "precio de bnb") se procesen antes.
      - Se eliminan términos genéricos ("bnb", "btc") de la condición compleja.
      - Para consultas complejas se envía un contexto fresco a OpenAI (sin historial previo) junto con un system prompt reforzado.
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

    # Actualizar historial (para otros casos) – aunque para respuestas técnicas complejas usaremos contexto fresco.
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    conversation_history[chat_id].append({"role": "user", "content": message_text})

    # Rama: Manejo de solicitudes pendientes (por ejemplo, datos históricos de cruces)
    if lower_msg in ["sí", "si", "por favor", "claro"]:
        if chat_id in pending_requests:
            if pending_requests[chat_id] == "historical_sma_crosses":
                try:
                    df = fetch_historical_data(SYMBOL, TIMEFRAME)
                    analysis = analyze_sma_crosses(df)
                    answer = f"Análisis histórico de cruces: {analysis}"
                    send_telegram_message(answer, chat_id)
                    conversation_history[chat_id].append({"role": "assistant", "content": answer})
                except Exception as e:
                    send_telegram_message(f"Error al obtener datos históricos: {e}", chat_id)
                del pending_requests[chat_id]
                return

    # Rama: Solicitud de gráfico (prioridad alta)
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

    # Rama: Solicitudes específicas para BTC en 1h (se procesan antes de las consultas generales)
    if "btc" in lower_msg and "1h" in lower_msg:
        try:
            btc_data = fetch_data("bitcoin", "1h")
            btc_indicators = calculate_indicators(btc_data)
            answer = (
                f"Indicadores BTC en 1h:\n"
                f"• Precio: ${btc_indicators['price']:.2f}\n"
                f"• RSI: {btc_indicators['rsi']:.2f}\n"
                f"• MACD: {btc_indicators['macd']:.2f} (Señal: {btc_indicators['macd_signal']:.2f})\n"
                f"• SMA10: {btc_indicators['sma_10']:.2f} | SMA25: {btc_indicators['sma_25']:.2f} | SMA50: {btc_indicators['sma_50']:.2f}"
            )
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id].append({"role": "assistant", "content": answer})
        except Exception as e:
            send_telegram_message("Agente, lo siento, no pude obtener datos técnicos en 1h para BTC. Consulta manualmente.", chat_id)
            print(f"[Error] BTC 1h: {e}")
        return

    # Rama: Consultas simples de precio
    if "precio" in lower_msg and not any(keyword in lower_msg for keyword in ["analiza", "análisis", "compara", "estrategia", "entrada", "puntos de entrada", "actualizacion"]):
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

    # Rama: Consultas simples de indicadores individuales (rsi, adx, macd, sma, cmf)
    if "rsi" in lower_msg and "indicador" not in lower_msg:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
            answer = f"ᛃ El RSI actual para {SYMBOL} es: {indicators['rsi']:.2f}"
            send_telegram_message(answer, chat_id)
            conversation_history[chat_id].append({"role": "assistant", "content": answer})
            print(f"[DEBUG] RSI enviado: {indicators['rsi']:.2f}")
        except Exception as e:
            send_telegram_message(f"Error al obtener el RSI: {e}", chat_id)
            print(f"[Error] RSI: {e}")
        return
    # (Bloques para ADX, MACD, SMA, CMF se mantienen similares)

    # Rama: Consultas complejas (análisis, comparaciones, estrategia, etc.)
    # Aquí eliminamos "bnb" y "btc" de la condición para que no interfiera con las consultas simples.
    if any(keyword in lower_msg for keyword in ["analiza", "análisis", "analisis", "compara", "estrategia", "entrada", "puntos de entrada", "actualizacion"]):
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            indicators = calculate_indicators(data)
        except Exception as e:
            fallback_context = (
                "Agente, actualmente se presenta una interferencia en la obtención de datos técnicos. "
                "Consulta manualmente en una plataforma de trading para obtener información actualizada."
            )
            send_telegram_message(fallback_context, chat_id)
            print(f"[Error] Datos técnicos: {e}")
            return

        # Se crea un contexto fresco sin incluir conversación previa para evitar respuestas de fallback.
        system_prompt = (
            "Eres Higgs, Agente X, un analista digital con acceso a datos técnicos actualizados del mercado. "
            "Tienes acceso en tiempo real a la información, y la siguiente es la data actualizada de indicadores técnicos. "
            "No digas que no tienes acceso a datos. Responde de forma precisa, concisa y con un toque de misterio, en español."
        )
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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
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
            error_msg = f"⚠️ Agente, hubo un error al procesar la solicitud: {e}"
            send_telegram_message(error_msg, chat_id)
            print(f"[Error] OpenAI: {e}")
        return

    # Rama: Consulta general (fallback)
    try:
        language = detect_language(message_text)
    except Exception as e:
        language = 'es'
        print(f"[Error] detect_language: {e}")
    fallback_msg = "Agente, no entendí tu consulta. Por favor, reformula tu solicitud."
    send_telegram_message(fallback_msg, chat_id)

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
