// =========================================================================
// OmniBot - Master UART ESP32 (4 Motores Stepper - A4988)
// Pines corregidos 
// =========================================================================

#include <Arduino.h>

#define UART_RX_PIN 16   // Conectar al Pin 8 (TX) de la Pi
#define UART_TX_PIN 17   // Conectar al Pin 10 (RX) de la Pi
#define UART_BAUD   115200
#define FRAME_SIZE  6

HardwareSerial PiSerial(2);

#define EN_PIN 25
const int stepPins[4] = {12, 27, 33, 18}; 
const int dirPins[4]  = {14, 26, 32, 19}; 

const float MAX_VELOCIDAD = 6400.0; 
const float ACELERACION   = 20.0;   

float vel_objetivo[4] = {0, 0, 0, 0};
float vel_actual[4]   = {0, 0, 0, 0};
unsigned long ultimo_micros_step[4] = {0, 0, 0, 0};
unsigned long ultimo_millis_rampa   = 0;

uint8_t frame[FRAME_SIZE];
uint8_t frameIdx = 0;
uint32_t lastByteMillis = 0;
const uint32_t FRAME_TIMEOUT_MS = 50;
unsigned long ultimaTramaRecibida = 0;
const unsigned long TIMEOUT_CONEXION_MS = 300; 

static inline uint8_t calc_checksum(uint8_t a, uint8_t b, uint8_t c, uint8_t d, uint8_t e) {
    return (uint8_t)(a ^ b ^ c ^ d ^ e);
}

void actualizarRampas() {
    unsigned long ahora = millis();
    if (ahora - ultimaTramaRecibida > TIMEOUT_CONEXION_MS) {
        for (int i = 0; i < 4; i++) vel_objetivo[i] = 0.0;
    }

    if (ahora - ultimo_millis_rampa >= 2) {
        ultimo_millis_rampa = ahora;
        for (int i = 0; i < 4; i++) {
            float diferencia = vel_objetivo[i] - vel_actual[i];
            if (abs(diferencia) <= ACELERACION) {
                vel_actual[i] = vel_objetivo[i];
            } else {
                if (diferencia > 0) vel_actual[i] += ACELERACION;
                else vel_actual[i] -= ACELERACION;
            }
            digitalWrite(dirPins[i], (vel_actual[i] >= 0) ? HIGH : LOW);
        }
    }
}

void generarPasos() {
    unsigned long ahora = micros();
    for (int i = 0; i < 4; i++) {
        if (abs(vel_actual[i]) < 10.0) continue; 
        unsigned long intervalo = (unsigned long)(1000000.0 / abs(vel_actual[i]));
        if (ahora - ultimo_micros_step[i] >= intervalo) {
            ultimo_micros_step[i] = ahora;
            digitalWrite(stepPins[i], HIGH);
            delayMicroseconds(2); 
            digitalWrite(stepPins[i], LOW);
        }
    }
}

void calcularCinematica(int rawX, int rawY, int rawR) {
    float x = (abs(rawX - 127) < 8) ? 0 : (rawX - 127);
    float y = (abs(rawY - 127) < 8) ? 0 : (rawY - 127);
    float r = (abs(rawR - 127) < 8) ? 0 : (rawR - 127);

    // =================================================================
    //Cambia a "1" para ENCENDER el motor, o "0" para APAGARLO.
    //Cambia la dir a "1" (Normal) o "-1" (Invertido).
    // =================================================================
    int M1_activo = 1;   int M1_dir = -1;   // Frontal Izquierdo
    int M2_activo = 1;   int M2_dir = 1;   // Frontal Derecho
    int M3_activo = 1;   int M3_dir = -1;   // Trasero Izquierdo
    int M4_activo = 1;   int M4_dir = 1;   // Trasero Derecho
    // =================================================================

    // Ecuaciones Mecanum puras (sin signos)
    float v1 = y + x + r; 
    float v2 = y - x - r; 
    float v3 = y - x + r; 
    float v4 = y + x - r; 

    // Aplicamos tus interruptores manuales a la velocidad objetivo
    vel_objetivo[0] = (v1 / 381.0) * MAX_VELOCIDAD * M1_activo * M1_dir;
    vel_objetivo[1] = (v2 / 381.0) * MAX_VELOCIDAD * M2_activo * M2_dir;
    vel_objetivo[2] = (v3 / 381.0) * MAX_VELOCIDAD * M3_activo * M3_dir;
    vel_objetivo[3] = (v4 / 381.0) * MAX_VELOCIDAD * M4_activo * M4_dir;
}

void setup() {
    Serial.begin(115200);
    PiSerial.begin(UART_BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN);

    pinMode(EN_PIN, OUTPUT);
    digitalWrite(EN_PIN, LOW);   

    for (int i = 0; i < 4; i++) {
        pinMode(stepPins[i], OUTPUT);
        pinMode(dirPins[i], OUTPUT);
        digitalWrite(stepPins[i], LOW); 
    }

    ultimaTramaRecibida = millis();
    Serial.println("OmniBot listo y sincronizado. Esperando comandos...");
}

void loop() {
    while (PiSerial.available()) {
        uint8_t b = PiSerial.read();
        uint32_t now = millis();

        if (frameIdx > 0 && (now - lastByteMillis) > FRAME_TIMEOUT_MS) {
            frameIdx = 0; 
        }
        lastByteMillis = now;

        if (frameIdx == 0) {
            if (b == 0xFF) frame[frameIdx++] = b;
        } else {
            frame[frameIdx++] = b;
            
            if (frameIdx == FRAME_SIZE) {
                uint8_t chk = calc_checksum(frame[0], frame[1], frame[2], frame[3], frame[4]);
                
                if (chk == frame[5]) {
                    ultimaTramaRecibida = millis(); 
                    calcularCinematica(frame[1], frame[2], frame[3]);
                    
                    Serial.printf("OK X=%d Y=%d R=%d | M1=%.0f M2=%.0f\n",
                                  frame[1], frame[2], frame[3], vel_objetivo[0], vel_objetivo[1]);
                } else {
                    Serial.println("Checksum invalido (Ruido en la linea)");
                }
                frameIdx = 0;
            }
        }
    }
    actualizarRampas();
    generarPasos();
}