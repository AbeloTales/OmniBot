import spidev
import time

# Configuración SPI
spi = spidev.SpiDev()
spi.open(0, 1)
spi.mode = 0b11
spi.max_speed_hz = 100000

print("Enviando señales de prueba al SPI...")
try:
    while True:
        # Enviamos un paquete de prueba constante
        spi.xfer2([255, 150, 100]) 
        print("Enviando: 255, 150, 100")
        time.sleep(1) # Envía cada segundo
except KeyboardInterrupt:
    spi.close()