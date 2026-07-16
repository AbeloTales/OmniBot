"""
Prueba aislada del protocolo SPI + handshake + checksum, SIN Flask ni
SocketIO ni threads adicionales. El objetivo es descartar si el problema
esta en el protocolo en si, o si es Flask/SocketIO quien mete el jitter
que lo rompe.

Corre esto en la Raspberry Pi mientras el ESP32 tiene cargado el firmware
refactorizado (con post_setup_cb / post_trans_cb).
"""
import spidev
import time
import RPi.GPIO as GPIO

HANDSHAKE_PIN = 17  # BCM17 = pin fisico 11

GPIO.setmode(GPIO.BCM)
GPIO.setup(HANDSHAKE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

spi = spidev.SpiDev()
spi.open(0, 1)
spi.mode = 0b01
spi.max_speed_hz = 50000  # misma velocidad que tu test que funcionaba 100%


def calc_checksum(a, b, c):
    return (a ^ b ^ c) & 0xFF


def esperar_handshake(timeout=0.2):
    t0 = time.time()
    while GPIO.input(HANDSHAKE_PIN) == 0:
        if time.time() - t0 > timeout:
            return False
        time.sleep(0.0005)
    return True


print("Enviando tramas de prueba con handshake...")
try:
    contador = 0
    while True:
        x = 150
        y = 100
        chk = calc_checksum(255, x, y)
        packet = [255, x, y, chk]

        t_espera_ini = time.time()
        ok = esperar_handshake()
        t_espera = time.time() - t_espera_ini

        if not ok:
            print(f"[{contador}] Timeout esperando handshake (esperó {t_espera*1000:.1f} ms)")
        else:
            resp = spi.xfer2(packet)
            print(f"[{contador}] Enviado: {packet}  (espera handshake: {t_espera*1000:.2f} ms)  Respuesta ESP32: {resp}")

        contador += 1
        time.sleep(1)  # igual que tu test original: 1 paquete por segundo
except KeyboardInterrupt:
    spi.close()
    GPIO.cleanup()