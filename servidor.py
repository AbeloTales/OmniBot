import spidev
import time
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

# Lock para asegurar que no se envíen paquetes simultáneos
spi_lock = threading.Lock()

# Configuración SPI
spi = spidev.SpiDev()
spi.open(0, 1)  
spi.mode = 0b01
spi.max_speed_hz = 50000

def enviar_spi(x, y):
    with spi_lock: # Solo un hilo puede usar el SPI a la vez
        val_x = max(0, min(254, int(x)))
        val_y = max(0, min(254, int(y)))
        
        # Paquete de 4 bytes
        packet = [255, val_x, val_y, 0]
        
        print(f"DEBUG SPI: Enviando {packet}")
        try:
            spi.xfer2(packet)
            time.sleep(0.01) # Pausa mínima para que el ESP32 respire
        except Exception as e:
            print(f"Error SPI: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('mensaje_tecla')
def handle_tecla(data):
    x = data.get('x', 127)
    y = data.get('y', 127)
    # Ejecutamos el envío en un thread separado para no bloquear el socket
    threading.Thread(target=enviar_spi, args=(x, y)).start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)