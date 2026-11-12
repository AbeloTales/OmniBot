# =========================================================================
# OmniBot - Master UART + Auto Video Streamer + Plataforma/Rotacion
# Version de Envio Continuo (Evita el Timeout del ESP32)
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
        "--port=8080", "--resolution=1280x720"
    ]
    try:
        camera_process = subprocess.Popen(
            comando_camara, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, preexec_fn=os.setsid
        )
        print("[CAMARA] Servidor ustreamer iniciado en puerto 8080 a 1280x720.")
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

def calc_checksum(a: int, b: int, c: int, d: int, e: int) -> int:
    return (a ^ b ^ c ^ d ^ e) & 0xFF

def uart_worker():
    # Valores por defecto (Robot detenido)
    current_x = 127
    current_y = 127
    current_r = 127
    current_p = 0

    while True:
        try:
            # Espera un nuevo comando máximo 0.05 segundos (50ms). 
            # Si no llega, lanza excepcion Empty y usa el comando anterior.
            x, y, r, p = cmd_queue.get(timeout=0.05)
            current_x, current_y, current_r, current_p = x, y, r, p
        except queue.Empty:
            pass # No hay datos nuevos, mantenemos el ultimo estado

        val_x = max(0, min(254, int(current_x)))
        val_y = max(0, min(254, int(current_y)))
        val_r = max(0, min(254, int(current_r)))
        val_p = max(0, min(2, int(current_p))) 

        chk = calc_checksum(0xFF, val_x, val_y, val_r, val_p)
        
        # Trama de 6 bytes
        packet = bytes([0xFF, val_x, val_y, val_r, val_p, chk])

        try:
            ser.write(packet)
            # Solo imprime en pantalla de vez en cuando (cada ~0.5s) para no saturar tu terminal
            if (val_x != 127 or val_y != 127 or val_r != 127) and (int(time.time() * 10) % 5 == 0):
                print(f"[UART] Enviando continuo X={val_x} Y={val_y} R={val_r} PLAT={val_p}")
        except Exception as e:
            pass

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
        socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
    finally:
        ser.close()
        detener_camara()