# PrintGraphic.py

import time
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Usa backend sin GUI
import matplotlib.pyplot as plt
import io
import requests
import re
from config import SYMBOL, TELEGRAM_TOKEN
import mplfinance as mpf
from market import fetch_data  # Ahora usa nuestra función actualizada de mercado

# Mapeo de posibles entradas a intervalos válidos
TIMEFRAME_MAPPING = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "10m": "5m",      # Si se ingresa 10m, lo mapeamos a 5m (ajustable)
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1d",
    "3d": "3d",
    "1w": "1w",
    "1M": "1M"
}

def extract_timeframe(text):
    """
    Extrae la temporalidad de la cadena 'text' utilizando regex.
    Retorna el valor mapeado o "1h" por defecto.
    """
    pattern = r'\b(\d+m|\d+h|\d+d|\d+w|\d+M)\b'
    matches = re.findall(pattern, text.lower())
    for match in matches:
        if match in TIMEFRAME_MAPPING:
            return TIMEFRAME_MAPPING[match]
    return "1h"

def fetch_chart_data(symbol=SYMBOL, timeframe="1h", limit=100):
    """Obtiene datos OHLCV para el gráfico usando la nueva función fetch_data."""
    data = fetch_data(symbol=symbol, timeframe=timeframe, limit=limit)
    data = data.copy()
    if 'volume' not in data.columns:
        data['volume'] = 0
    return data

def send_graphic(chat_id, timeframe_input="1h", chart_type="line"):
    """
    Genera un gráfico de las últimas velas y lo envía a Telegram.
    Parámetros:
      - timeframe_input: temporalidad solicitada (se mapea a un valor válido).
      - chart_type: 'line' para gráfico lineal o 'candlestick' para velas japonesas.
    """
    try:
        # Extraer y validar el timeframe
        timeframe = extract_timeframe(timeframe_input)
        data = fetch_chart_data(SYMBOL, timeframe, limit=100)
        
        # Calcular soportes, resistencias y medias móviles
        support = data['close'].min()
        resistance = data['close'].max()
        sma20 = data['close'].rolling(window=20).mean()
        sma50 = data['close'].rolling(window=50).mean()
        
        buf = io.BytesIO()
        caption = f"Gráfico de {SYMBOL} - {timeframe}"
        
        # Crear un estilo futurista personalizado
        mc = mpf.make_marketcolors(
            up='#00ff00',    # verde neón
            down='#ff4500',  # rojo neón
            edge={'up': '#00ff00', 'down': '#ff4500'},
            wick={'up': '#00ff00', 'down': '#ff4500'},
            volume='#555555'
        )
        futuristic_style = mpf.make_mpf_style(
            base_mpf_style='nightclouds',
            marketcolors=mc,
            facecolor='#0f0f0f',
            gridstyle='--',
            rc={
                'font.size': 10,
                'figure.facecolor': '#0f0f0f',
                'axes.facecolor': '#0f0f0f',
                'axes.edgecolor': 'white',
                'axes.labelcolor': 'white',
                'xtick.color': 'white',
                'ytick.color': 'white'
            }
        )
        
        if chart_type.lower() == "candlestick":
            # Preparar líneas para SMA y soporte/resistencia
            ap0 = mpf.make_addplot(sma20, color='#00ffff', width=1.0, linestyle='-')
            ap1 = mpf.make_addplot(sma50, color='#ff00ff', width=1.0, linestyle='-')
            sr_support = [support] * len(data)
            sr_resistance = [resistance] * len(data)
            ap2 = mpf.make_addplot(sr_support, color='yellow', linestyle='--', width=0.8)
            ap3 = mpf.make_addplot(sr_resistance, color='orange', linestyle='--', width=0.8)
            fig, axlist = mpf.plot(
                data,
                type='candle',
                style=futuristic_style,
                title=caption,
                volume=False,
                addplot=[ap0, ap1, ap2, ap3],
                returnfig=True
            )
            fig.suptitle(caption, y=0.95, fontsize=16, color='white')
            fig.savefig(buf, dpi=150, format='png')
            plt.close(fig)
        else:
            # Gráfico lineal con diseño futurista
            plt.figure(figsize=(10, 6))
            plt.plot(data.index, data['close'], label="Precio", color='#00ff00')
            plt.plot(data.index, sma20, label="SMA20", color='#00ffff')
            plt.plot(data.index, sma50, label="SMA50", color='#ff00ff')
            plt.axhline(support, color='yellow', linestyle='--', label="Soporte")
            plt.axhline(resistance, color='orange', linestyle='--', label="Resistencia")
            plt.title(caption, fontsize=16, color='white')
            plt.xlabel("Tiempo", color='white')
            plt.ylabel("Precio", color='white')
            plt.legend()
            plt.grid(True, linestyle="--", alpha=0.7, color='gray')
            plt.gca().set_facecolor('#0f0f0f')
            plt.savefig(buf, format="png")
            plt.close()
        
        buf.seek(0)
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        files = {'photo': buf}
        data_payload = {'chat_id': chat_id, 'caption': caption}
        response = requests.post(url, data=data_payload, files=files)
        if response.status_code != 200:
            print(f"Error al enviar el gráfico: {response.text}")
    except Exception as e:
        print(f"Error en PrintGraphic.send_graphic: {e}")
