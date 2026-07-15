from flask import Flask, render_template
from flask_socketio import SocketIO
import spidev
import time

# Configuración del servidor Web y WebSockets
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuración de comunicación por bus SPI hacia el microcontrolador
spi = spidev.SpiDev()
try:
    # Abrimos bus 0, dispositivo 0 (pines estándar físicos SPI en la Raspberry Pi)
    spi.open(0, 0)
    spi.max_speed_hz = 1000000  # Velocidad: 1 MHz
    spi_habilitado = True
    print(" [OK] Hardware SPI inicializado y listo para transmitir.")
except Exception as e:
    print(f" [ADVERTENCIA] No se pudo abrir el bus SPI. ¿Está activado en dietpi-config? Detalle: {e}")
    spi_habilitado = False

@app.route('/')
def index():
    # Renderiza y envía la interfaz universal HTML al navegador de tu laptop
    return render_template('index.html')

@socketio.on('comando_movimiento')
def procesar_movimiento(datos):
    vx = datos.get('x', 0)
    vy = datos.get('y', 0)
    
    # Consola de depuración (visible en la terminal si estás conectado por SSH)
    print(f" -> Vector recibido | X: {vx} | Y: {vy}")
    
    if spi_habilitado:
        # Conversión del rango vectorial [-1 a 1] a bytes sin signo [0 a 255]
        # Reposo / Freno = 127
        byte_x = int((vx + 1) * 127.5)
        byte_y = int((vy + 1) * 127.5)
        
        # Trama de datos: [Byte de inicio (255), Eje X, Eje Y]
        trama = [255, byte_x, byte_y]
        
        # Enviar ráfaga al microcontrolador
        spi.xfer2(trama)

if __name__ == '__main__':
    print(" ========================================================")
    print("  Iniciando servidor de OmniBot en el puerto 5000...")
    print("  Accede desde el navegador de tu laptop en: http://192.168.100.66:5000")
    print(" ========================================================")
    # Se ejecuta en todas las interfaces de red de la Raspberry (0.0.0.0)
    socketio.run(app, host='0.0.0.0', port=5000)