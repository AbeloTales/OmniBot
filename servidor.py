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

import RPi.GPIO as GPIO
from flask import Flask, render_template
from flask_socketio import SocketIO

# --- Configuracion de pines ---------------------------------------------
HANDSHAKE_PIN = 17  # GPIO de la Pi conectado al GPIO4 (handshake) del ESP32

GPIO.setmode(GPIO.BCM)
GPIO.setup(HANDSHAKE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

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


def esperar_handshake(timeout: float = 0.05) -> bool:
    """Bloquea hasta que el ESP32 indique que ya armo la transaccion SPI,
    o hasta agotar el timeout (en segundos)."""
    t0 = time.time()
    while GPIO.input(HANDSHAKE_PIN) == 0:
        if time.time() - t0 > timeout:
            return False
        time.sleep(0.0005)
    return True


def spi_worker():
    """Unico hilo que efectivamente toca el bus SPI. Evita condiciones de
    carrera entre transacciones y hace innecesario el Lock manual."""
    while True:
        x, y = cmd_queue.get()

        val_x = max(0, min(254, int(x)))
        val_y = max(0, min(254, int(y)))
        chk = calc_checksum(255, val_x, val_y)
        packet = [255, val_x, val_y, chk]

        if not esperar_handshake():
            print("[SPI] Timeout esperando handshake del ESP32, se descarta la trama")
            continue

        try:
            resp = spi.xfer2(packet)
            # resp trae el eco tx_buf del ESP32: [0xAA, X_echo, Y_echo, chk]
            # se puede validar aca si se quiere confirmar que el ESP32
            # efectivamente aplico el comando anterior.
        except Exception as e:
            print(f"[SPI] Error en xfer2: {e}")


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
        GPIO.cleanup()
        spi.close()