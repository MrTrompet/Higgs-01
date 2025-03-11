import time
import logging
from market import fetch_data, fetch_btc_price, fetch_historical_data
from indicators import fetch_btc_dominance
from ml_model import aggregate_signals
from telegram_handler import send_telegram_message
from config import TIMEFRAME
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from btc_indicators import get_btc_indicators  # Importación desde el nuevo módulo

def monitor_market():
    """
    Monitorea el mercado cada 5 minutos.
    Evalúa señales para BNB (usando aggregate_signals) y para BTC (verificando dominancia y precio).
    """
    logging.info("Iniciando monitoreo del mercado con la nueva estrategia (cada 5 minutos)...")
    last_btc_dominance = None
    last_btc_price = None

    while True:
        try:
            # Monitoreo para BNB
            data_bnb = fetch_data("bnb", TIMEFRAME)
            signal_message = aggregate_signals(data_bnb)
            if signal_message:
                msg = "Señales detectadas:\n" + signal_message
                send_telegram_message(msg)
                logging.info("Señales enviadas a Telegram.")
            else:
                logging.info("No se detectaron señales en este ciclo para BNB.")

            # Monitoreo para BTC utilizando get_btc_indicators()
            btc_indicators = get_btc_indicators()
            btc_price = btc_indicators['price']
            btc_dominance = btc_indicators['dominance']
            if last_btc_dominance is not None and last_btc_price is not None:
                if btc_price < last_btc_price and btc_dominance > last_btc_dominance:
                    alert = (
                        "📡 Alerta de manipulación: BTC cae pero la dominancia aumenta. "
                        "Podrías revisar una entrada en corto para altcoins."
                    )
                    send_telegram_message(alert)
                    logging.info("Alerta de manipulación enviada a Telegram.")
            last_btc_dominance = btc_dominance
            last_btc_price = btc_price

            time.sleep(300)  # Espera 5 minutos
        except Exception as e:
            logging.error("Error en monitor_market: %s", e)
            time.sleep(60)

if __name__ == "__main__":
    monitor_market()
