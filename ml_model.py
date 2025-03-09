from indicators import calculate_indicators, check_cross_signals

def aggregate_signals(data):
    """
    Agrega señales basadas en los indicadores técnicos:
      - Señal de entrada si el precio cruza por encima de la banda superior de Bollinger y las bandas convergen.
      - Golden Cross o Death Cross en SMAs de 10, 25 y 50.
    Retorna un mensaje con las señales detectadas (si las hay).
    """
    indicators = calculate_indicators(data)
    message = ""
    price = indicators['price']
    bb_high = indicators['bb_high']
    bb_low = indicators['bb_low']
    
    # Umbral para convergencia: diferencia menor al 0.5% del precio
    convergence_threshold = 0.005 * price
    if (bb_high - bb_low) < convergence_threshold and price > bb_high:
        message += "Señal de entrada: Precio cruza banda superior con bandas convergiendo.\n"
    
    golden_cross, death_cross = check_cross_signals(data)
    if golden_cross:
        message += "Golden Cross detectado en SMA (10, 25, 50).\n"
    if death_cross:
        message += "Death Cross detectado en SMA (10, 25, 50).\n"
    
    return message.strip()
