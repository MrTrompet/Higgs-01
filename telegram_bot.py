import time
from telegram_handler import get_updates, handle_telegram_message

def telegram_bot_loop():
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            if updates:
                for update in updates:
                    handle_telegram_message(update)
                    offset = update["update_id"] + 1
            time.sleep(3)
        except Exception as e:
            print(f"[Error] En el bucle del bot: {e}")
            time.sleep(10)
