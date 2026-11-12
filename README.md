# OmniBot

OmniBot es una plataforma robótica móvil omnidireccional equipada con 4 ruedas Mecanum y operada de forma remota. El sistema utiliza una arquitectura distribuida que integra una Raspberry Pi para el servidor de teleoperación web y el streaming de video, junto con un ESP32 para el control de hardware de bajo nivel.

![Arquitectura del Sistema](./System_Arquitecture.png)

## 🚀 Características Principales

*   **Movimiento Omnidireccional:** Plataforma impulsada por motores paso a paso y ruedas Mecanum (con rodillos de 14 mm impresos en 3D).
*   **Teleoperación Web en Tiempo Real:** Interfaz de control desarrollada con Flask y SocketIO. Los eventos web se capturan con JavaScript y se procesan en el servidor.
*   **Visión Artificial / Streaming:** Captura de video en alta resolución (ej. 1920x1080) utilizando `ustreamer`, lanzado y gestionado como un subproceso (`subprocess`) desde Python.
*   **Comunicación Segura UART:** Enlace serial entre la Raspberry Pi y el ESP32 utilizando tramas de datos estructuradas con Checksum para garantizar la integridad de las señales de los motores.

## 📂 Estructura del Repositorio

*   📁 **`Control_Script/`**: Scripts principales en Python para el servidor Flask, gestión de WebSockets y la lógica de envío serial.[cite: 1]
*   📁 **`Electronic_Design/`**: Esquemáticos y diseños de placas de circuito impreso (PCB) para la integración de los drivers DRV8825 y el microcontrolador.[cite: 1]
*   📁 **`Mechanic_Design/`**: Modelado CAD 3D de la estructura mecánica, incluyendo bocetos preliminares y piezas para impresión 3D (Ender 3 V2).[cite: 1]
*   📁 **`System_Scripts/`**: Scripts del sistema (bash/python) utilizados para levantar procesos auxiliares, como el stream de la cámara con ustreamer.[cite: 1]

*(Nota: Consulta los archivos `.png` en la raíz como `Controls_Mapping.png` y `Mechanism_Sketch.png` para ver los esquemas y distribuciones).*[cite: 1]

## 🛠️ Tecnologías y Dependencias

Para el entorno del servidor en la Raspberry Pi, el proyecto requiere las siguientes dependencias de Python:

*   `flask`
*   `flask-socketio`
*   `simple-websocket`
*   `pyserial`

**Dependencias del Sistema:**
*   `ustreamer` (Debe estar compilado/instalado en la Raspberry Pi para la captura y transmisión de imagen).

## ⚙️ Instalación y Uso

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/AbeloTales/OmniBot.git](https://github.com/AbeloTales/OmniBot.git)
   cd OmniBot
