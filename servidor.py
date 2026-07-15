from flask import Flask, render_template
from flask_socketio import SocketIO
import spidev
import logging

# Configuración inicial de Flask y SocketIO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Configuración SPI ---
spi = spidev.SpiDev()
try:
    spi.open(0, 0) # Puerto 0, Chip Select 0
    spi.mode = 0b00
    spi.max_speed_hz = 100000 # 100kHz para máxima estabilidad
    print("SPI configurado correctamente.")
except Exception as e:
    print(f"Error al abrir SPI: {e}")

def enviar_spi(x, y):
    """
    Envía una trama de 3 bytes [255, X, Y] al ESP32.
    """
    # Mapeo: aseguramos que los valores estén entre 0 y 254
    # (Reservamos 255 como byte de inicio para sincronización)
    val_x = max(0, min(254, int(x)))
    val_y = max(0, min(254, int(y)))
    
    try:
        spi.xfer2([255, val_x, val_y])
    except Exception as e:
        print(f"Error enviando SPI: {e}")

# --- Rutas de Flask ---
@app.route('/')
def index():
    return render_template('index.html')

# --- Manejo de eventos de SocketIO (Teleoperación) ---
@socketio.on('connect')
def test_connect():
    print("Cliente conectado")

@socketio.on('mensaje_tecla') # Ajusta este nombre al que uses en tu JS
def handle_tecla(data):
    # 'data' debería traer algo como {'x': 127, 'y': 127}
    x = data.get('x', 127)
    y = data.get('y', 127)
    
    print(f"Comando recibido: X={x}, Y={y}")
    
    # Enviar al ESP32 vía SPI
    enviar_spi(x, y)

if __name__ == '__main__':
    print("Iniciando servidor de OmniBot...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)