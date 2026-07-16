# =========================================================================
# OmniBot - Master UART (Raspberry Pi)
# Reemplaza el envio por SPI (driver spi_slave inestable en el ESP32) por
# comunicacion serie simple via pyserial.
# =========================================================================
# Requisitos:
#   pip install pyserial flask flask-socketio
#
# Antes de correr esto, habilitar el puerto serie por hardware:
#   sudo raspi-config -> Interface Options -> Serial Port
#     "login shell over serial"      -> No
#     "serial port hardware enabled" -> Yes
#   Reiniciar despues.
# =========================================================================

import serial
import time
import threading
import queue

from flask import Flask, render_template
from flask_socketio import SocketIO

# --- Configuracion UART ---------------------------------------------------
SERIAL_PORT = '/dev/serial0'   # en RPi4 tambien puede ser /dev/ttyAMA0
BAUD_RATE = 115200

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

app = Flask(__name__)
socketio = SocketIO(app)

cmd_queue = queue.Queue(maxsize=1)


def calc_checksum(a: int, b: int, c: int) -> int:
    return (a ^ b ^ c) & 0xFF


def uart_worker():
    """Unico hilo que efectivamente escribe en el puerto serie. Evita
    condiciones de carrera entre envios."""
    ultimo_envio = 0.0
    intervalo_minimo = 0.01  # 10 ms entre tramas (~100 Hz max), ajustable

    while True:
        x, y = cmd_queue.get()

        espera = intervalo_minimo - (time.time() - ultimo_envio)
        if espera > 0:
            time.sleep(espera)

        val_x = max(0, min(254, int(x)))
        val_y = max(0, min(254, int(y)))
        chk = calc_checksum(0xFF, val_x, val_y)
        packet = bytes([0xFF, val_x, val_y, chk])

        try:
            ser.write(packet)
            print(f"[UART] Enviado x={val_x} y={val_y}")
        except Exception as e:
            print(f"[UART] Error: {e}")

        ultimo_envio = time.time()


threading.Thread(target=uart_worker, daemon=True).start()


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('mensaje_tecla')
def handle_tecla(data):
    x = data.get('x', 127)
    y = data.get('y', 127)

    if cmd_queue.full():
        try:
            cmd_queue.get_nowait()
        except queue.Empty:
            pass
    cmd_queue.put((x, y))


if __name__ == '__main__':
    try:
        socketio.run(app, host='0.0.0.0', port=5000)
    finally:
        ser.close()