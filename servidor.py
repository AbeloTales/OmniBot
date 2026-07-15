import spidev
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

# Configuración SPI
spi = spidev.SpiDev()
spi.open(0, 1)        # Canal 1 (CE1) - Pin físico 26
spi.mode = 0b01       # Modo 1 verificado
spi.max_speed_hz = 50000  # Velocidad estable de 50kHz

def enviar_spi(x, y):
    # Limitamos los valores entre 0 y 254
    val_x = max(0, min(254, int(x)))
    val_y = max(0, min(254, int(y)))
    
    # Paquete de 4 bytes (Byte de inicio, X, Y, y un cero de relleno de seguridad)
    packet = [255, val_x, val_y, 0]
    
    # Imprime en la terminal de la Pi lo que se está enviando
    print(f"DEBUG SPI: Enviando {packet}")
    try:
        spi.xfer2(packet)
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
    # Se ejecuta en el puerto 5000
    socketio.run(app, host='0.0.0.0', port=5000)