# telegram_bot.py
import time
from telegram_handler import get_updates, handle_telegram_message

def telegram_bot_loop():
    last_update_id = None
    while True:
        try:
            updates = get_updates()
            if updates:
                for update in updates:
                    update_id = update.get("update_id")
                    if last_update_id is None or update_id > last_update_id:
                        handle_telegram_message(update)
                        last_update_id = update_id
            time.sleep(3)
        except Exception as e:
            print(f"Error en el bucle del bot: {e}")
            time.sleep(10)
