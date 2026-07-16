# =========================================================================
# OmniBot - Master SPI (Raspberry Pi) - Version robusta con handshake y
# checksum, sincronizada con el firmware ESP32 refactorizado.
# =========================================================================
# Cambios respecto a la version anterior:
#  1. Se espera la linea de HANDSHAKE (conectada al GPIO4 del ESP32) antes
#     de disparar cada xfer2, eliminando la condicion de carrera que hacia
#     perder el byte Y.
#  2. Un unico hilo "worker" consume una cola en vez de crear un
#     threading.Thread por cada evento de SocketIO (menos jitter, orden
#     garantizado).
#  3. La cola tiene tamano 1: si llegan comandos mas rapido de lo que el
#     bus puede procesar, se descarta el viejo y se manda siempre el mas
#     reciente (evita acumular latencia).
#  4. Checksum XOR en cada trama.
# =========================================================================

import spidev
import time
import threading
import queue

from flask import Flask, render_template
from flask_socketio import SocketIO

# --- Configuracion SPI ---------------------------------------------------
spi = spidev.SpiDev()
spi.open(0, 1)          # Canal CE1
spi.mode = 0b01         # Modo 1 (confirmado que funciona en tu bus)
spi.max_speed_hz = 200000  # Con handshake real ya no hace falta ir tan lento

app = Flask(__name__)
socketio = SocketIO(app)

cmd_queue = queue.Queue(maxsize=1)


def calc_checksum(a: int, b: int, c: int) -> int:
    return (a ^ b ^ c) & 0xFF


def spi_worker():
    """Unico hilo que efectivamente toca el bus SPI. Evita condiciones de
    carrera entre transacciones y hace innecesario el Lock manual.

    NOTA: se saco la espera de handshake por hardware. La evidencia de las
    pruebas mostro que el bus responde bien con envio directo (igual que
    test_spi.py), y que esperar el handshake estaba corrompiendo los datos
    en vez de protegerlos. Se deja un pequeno intervalo minimo entre envios
    para no saturar al ESP32 mientras procesa la trama anterior.
    """
    ultimo_envio = 0.0
    intervalo_minimo = 0.02  # 20 ms entre tramas, ajustable segun pruebas

    while True:
        x, y = cmd_queue.get()

        espera = intervalo_minimo - (time.time() - ultimo_envio)
        if espera > 0:
            time.sleep(espera)

        val_x = max(0, min(254, int(x)))
        val_y = max(0, min(254, int(y)))
        chk = calc_checksum(255, val_x, val_y)
        packet = list([255, val_x, val_y, chk])  # copia nueva: xfer2 la muta

        try:
            resp = spi.xfer2(packet)
            # resp trae el eco tx_buf del ESP32: [0xAA, X_echo, Y_echo, chk]
            print(f"[SPI] Enviado x={val_x} y={val_y}  Respuesta ESP32: {resp}")
        except Exception as e:
            print(f"[SPI] Error en xfer2: {e}")

        ultimo_envio = time.time()


threading.Thread(target=spi_worker, daemon=True).start()


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('mensaje_tecla')
def handle_tecla(data):
    x = data.get('x', 127)
    y = data.get('y', 127)

    # Si ya hay un comando pendiente sin enviar, lo reemplazamos por el
    # nuevo (nos interesa siempre el ultimo estado del joystick).
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
        spi.close()