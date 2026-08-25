# =========================================================================
# OmniBot - Master UART + Auto Video Streamer + Plataforma/Rotacion
# =========================================================================

import serial
import time
import threading
import queue
import subprocess
import os
import signal

from flask import Flask, render_template
from flask_socketio import SocketIO

# --- Configuracion UART ---
SERIAL_PORT = '/dev/serial0'
BAUD_RATE = 115200

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

app = Flask(__name__)
socketio = SocketIO(app)
cmd_queue = queue.Queue(maxsize=1)
camera_process = None

def iniciar_camara():
    global camera_process
    comando_camara = [
        "ustreamer", "--device=/dev/video0", "--host=0.0.0.0", 
        "--port=8080", "--resolution=640x480"
    ]
    try:
        camera_process = subprocess.Popen(
            comando_camara, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, preexec_fn=os.setsid
        )
        print("[CAMARA] Servidor ustreamer iniciado en puerto 8080.")
    except Exception as e:
        print(f"[CAMARA] Error al iniciar la camara: {e}")

def detener_camara():
    global camera_process
    if camera_process is not None:
        try:
            os.killpg(os.getpgid(camera_process.pid), signal.SIGTERM)
            print("[CAMARA] Proceso de camara detenido.")
        except Exception as e:
            print(f"[CAMARA] Error: {e}")

# Nuevo calculo de checksum considerando 5 bytes de datos
def calc_checksum(a: int, b: int, c: int, d: int, e: int) -> int:
    return (a ^ b ^ c ^ d ^ e) & 0xFF

def uart_worker():
    ultimo_envio = 0.0
    intervalo_minimo = 0.01  # 100 Hz max

    while True:
        x, y, r, p = cmd_queue.get()

        espera = intervalo_minimo - (time.time() - ultimo_envio)
        if espera > 0:
            time.sleep(espera)

        val_x = max(0, min(254, int(x)))
        val_y = max(0, min(254, int(y)))
        val_r = max(0, min(254, int(r)))
        val_p = max(0, min(2, int(p))) # 0=Stop, 1=Subir, 2=Bajar

        chk = calc_checksum(0xFF, val_x, val_y, val_r, val_p)
        
        # Trama de 6 bytes
        packet = bytes([0xFF, val_x, val_y, val_r, val_p, chk])

        try:
            ser.write(packet)
            # Solo imprime si alguien presiona la plataforma o se mueve, para evitar spam
            if val_p != 0 or val_x != 127 or val_y != 127 or val_r != 127:
                print(f"[UART] X={val_x} Y={val_y} R={val_r} PLAT={val_p}")
        except Exception as e:
            print(f"[UART] Error: {e}")

        ultimo_envio = time.time()

threading.Thread(target=uart_worker, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('mensaje_tecla')
def handle_tecla(data):
    # Recupera los 4 valores desde la web
    x = data.get('x', 127)
    y = data.get('y', 127)
    r = data.get('r', 127)
    p = data.get('p', 0)

    if cmd_queue.full():
        try:
            cmd_queue.get_nowait()
        except queue.Empty:
            pass
    cmd_queue.put((x, y, r, p))

if __name__ == '__main__':
    iniciar_camara()
    try:
        socketio.run(app, host='0.0.0.0', port=5000)
    finally:
        ser.close()
        detener_camara()