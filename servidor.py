import spidev
import time
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

# Configuración SPI
spi = spidev.SpiDev()
spi.open(0, 1)  
spi.mode = 0b01
spi.max_speed_hz = 50000

# VARIABLES DE ESTADO GLOBALES (El estado actual del robot)
estado_robot = {
    'x': 127,
    'y': 127
}

# 1. HILO TRABAJADOR: Se ejecuta en el fondo como test_spi.py
def bucle_spi_permanente():
    while True:
        # Leemos las variables en memoria
        val_x = max(0, min(254, int(estado_robot['x'])))
        val_y = max(0, min(254, int(estado_robot['y'])))
        
        packet = [255, val_x, val_y, 0]
        
        try:
            spi.xfer2(packet)
        except Exception as e:
            print(f"Error SPI: {e}")
            
        # Enviamos exactamente 20 veces por segundo (50ms de pausa)
        # Esto le da al ESP32 la paz y estabilidad que tenía en test_spi.py
        time.sleep(0.05) 

@app.route('/')
def index():
    return render_template('index.html')

# 2. EVENTO WEB: Ya NO toca el SPI, solo actualiza la memoria al instante
@socketio.on('mensaje_tecla')
def handle_tecla(data):
    estado_robot['x'] = data.get('x', 127)
    estado_robot['y'] = data.get('y', 127)
    # Cero bloqueos, cero hilos nuevos, respuesta web instantánea

if __name__ == '__main__':
    # Iniciamos el bucle SPI en un SOLO hilo secundario antes de arrancar la web
    hilo_spi = threading.Thread(target=bucle_spi_permanente, daemon=True)
    hilo_spi.start()
    
    print("Servidor iniciado. Bucle SPI corriendo a 20Hz...")
    socketio.run(app, host='0.0.0.0', port=5000)