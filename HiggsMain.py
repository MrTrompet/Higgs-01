#!/usr/bin/env python
import threading
import time
from monitor_market import monitor_market
from telegram_bot import telegram_bot_loop

def main():
    # Iniciar el monitoreo del mercado
    market_thread = threading.Thread(target=monitor_market, daemon=True)
    market_thread.start()
    
    # Iniciar el bot de Telegram
    telegram_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    telegram_thread.start()
    
    # Mantener el proceso principal vivo
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
