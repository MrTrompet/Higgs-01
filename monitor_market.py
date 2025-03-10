import time
import logging
from market import fetch_data, fetch_btc_price
from indicators import fetch_btc_dominance
from ml_model import aggregate_signals
from telegram_handler import send_telegram_message
from config import TIMEFRAME

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
            
            # Evaluar señales técnicas
            signal_message = aggregate_signals(data)
            if signal_message:
                msg = "Señales detectadas:\n" + signal_message
                send_telegram_message(msg)
                logging.info("Señales enviadas a Telegram.")
            else:
                logging.info("No se detectaron señales en este ciclo.")
            
            # Verificar dominancia de BTC
            btc_dominance = fetch_btc_dominance()
            btc_price = fetch_btc_price()
            if last_btc_dominance is not None and last_btc_price is not None:
                if btc_price < last_btc_price and btc_dominance > last_btc_dominance:
                    alert = (
                        "📡Alerta de manipulación: BTC cae pero la dominancia aumenta. "
                        "Se podria revisar una entrada en corto para altcoins, agente podrias hacer un analisis del total 2, seguire escaneando..."
                    )
                    send_telegram_message(alert)
                    logging.info("Alerta de manipulación enviada a Telegram.")
            last_btc_dominance = btc_dominance
            last_btc_price = btc_price
            
            time.sleep(300)
        except Exception as e:
            logging.error("Error en monitor_market: %s", e)
            time.sleep(60)

if __name__ == "__main__":
    monitor_market()
