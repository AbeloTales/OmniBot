import spidev
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

# Configuración SPI
# Usamos canal 1 (CE1) como verificamos en las pruebas
spi = spidev.SpiDev()
spi.open(0, 1)  
spi.mode = 0b01  # Modo verificado para comunicación estable
spi.max_speed_hz = 50000  # Velocidad ajustada para evitar ruido

def enviar_spi(x, y):
    # Aseguramos que los valores estén entre 0 y 254 (sin usar 255 para evitar conflictos con el byte de inicio)
    val_x = max(0, min(254, int(x)))
    val_y = max(0, min(254, int(y)))
    
    # Debug: Esto te ayudará a confirmar si el problema es el Python o el ESP32
    print(f"DEBUG SPI: Enviando [255, {val_x}, {val_y}]")
    
    try:
        spi.xfer2([255, val_x, val_y])
    except Exception as e:
        print(f"Error al enviar por SPI: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('mensaje_tecla')
def handle_tecla(data):
    x = data.get('x', 127)
    y = data.get('y', 127)
    print(f"Comando recibido web: X={x}, Y={y}")
    enviar_spi(x, y)

if __name__ == '__main__':
    # Ejecutar con sudo para permisos de SPI
    socketio.run(app, host='0.0.0.0', port=5000)