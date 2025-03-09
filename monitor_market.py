#!/usr/bin/env python
import time
import logging
from market import fetch_data, fetch_btc_price
from indicators import fetch_btc_dominance
from ml_model import aggregate_signals
from telegram_handler import send_telegram_message
from config import TIMEFRAME

# Configuración del logging para mensajes profesionales
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def monitor_market():
    logging.info("Iniciando monitoreo del mercado con la nueva estrategia (cada 5 minutos)...")
    last_btc_dominance = None
    last_btc_price = None

    while True:
        try:
            data = fetch_data(timeframe=TIMEFRAME)
            
            # Se evalúan las señales técnicas robustas
            signal_message = aggregate_signals(data)
            if signal_message:
                telegram_msg = "Señales detectadas:\n" + signal_message
                send_telegram_message(telegram_msg)
                logging.info("Señales enviadas a Telegram.")
            else:
                # En Railway solo se loguea, sin enviar a Telegram
                logging.info("No se detectaron señales en este ciclo.")

            # Verificar dominancia de BTC para detectar manipulación
            btc_dominance = fetch_btc_dominance()
            btc_price = fetch_btc_price()
            if last_btc_dominance is not None and last_btc_price is not None:
                if btc_price < last_btc_price and btc_dominance > last_btc_dominance:
                    alert_msg = (
                        "Alerta de manipulación: BTC cae pero la dominancia aumenta. "
                        "Posible entrada en corto para altcoins."
                    )
                    send_telegram_message(alert_msg)
                    logging.info("Alerta de manipulación enviada a Telegram.")
            last_btc_dominance = btc_dominance
            last_btc_price = btc_price
            
            # Espera de 5 minutos (300 segundos) antes del siguiente ciclo
            time.sleep(300)
        except Exception as e:
            logging.error("Error en monitor_market: %s", e)
            time.sleep(60)

if __name__ == "__main__":
    monitor_market()
