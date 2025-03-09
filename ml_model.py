# ml_model.py
from indicators import calculate_indicators, check_cross_signals

def aggregate_signals(data):
    """
    Agrega señales basadas en los indicadores técnicos:
      - Si el precio cruza por encima de la banda superior de Bollinger y las bandas se están acercando (convergencia).
      - Se detecta un Golden Cross o Death Cross en las SMAs (10, 25 y 50).
    Retorna un mensaje con las señales detectadas (si las hay).
    """
    indicators = calculate_indicators(data)
    message = ""
    price = indicators['price']
    bb_high = indicators['bb_high']
    bb_low = indicators['bb_low']
    rsi = indicators['rsi']
    
    # Umbral para considerar convergencia: diferencia menor al 0.5% del precio
    convergence_threshold = 0.005 * price
    if (bb_high - bb_low) < convergence_threshold and price > bb_high:
        message += "Señal de entrada: Precio cruza banda superior con bandas convergiendo.\n"
    
    golden_cross, death_cross = check_cross_signals(data)
    if golden_cross:
        message += "Golden Cross detectado en SMA (10, 25, 50).\n"
    if death_cross:
        message += "Death Cross detectado en SMA (10, 25, 50).\n"
    
    # Aquí se pueden añadir condiciones adicionales (por ejemplo, basadas en RSI) según se requiera.
    return message.strip()
