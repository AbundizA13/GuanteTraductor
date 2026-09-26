"""Lee el IMU por USB, estima la orientacion y dice palabras al detectar gestos.

Uso:   python reconocer_gestos.py            (Monitor Serie de Arduino CERRADO)
       python reconocer_gestos.py --debug    (imprime elevacion y picos del giroscopio)
"""
import sys, time
import numpy as np
import serial

from fusion import actualizar, elevacion_deg
from gestos import DetectorHola, DetectorBajada

# ---------------- CONFIGURACION ----------------
PUERTO = "COM5"                                # el puerto que veas en Administrador de dispositivos
BAUD = 115200
NOMBRE = "TU NOMBRE"                           # para la frase "Yo soy <nombre>"
# Direccion de los dedos en ejes del chip. USA EL MISMO VALOR que te funciono en la
# visualizacion 3D (tecla 'i' de demo_mano_3d invierte su signo).
HAND_FWD = np.array([0.0, -1.0, 0.0])
DEBUG = "--debug" in sys.argv
# -----------------------------------------------

try:
    import pyttsx3                             # voz offline (pip install pyttsx3)
    _voz = pyttsx3.init()
except Exception:
    _voz = None


def decir(texto):
    print(f">>> {texto}")
    if _voz:
        _voz.say(texto)
        _voz.runAndWait()


ser = serial.Serial(PUERTO, BAUD, timeout=0.01)
time.sleep(1.5)
ser.reset_input_buffer()


def leer_muestras():
    out = []
    while ser.in_waiting:
        try:
            p = ser.readline().decode(errors="ignore").strip().split(",")
            if len(p) == 7:
                out.append([float(x) for x in p])
        except ValueError:
            pass
    return out


print("Deja el reloj QUIETO 2 s (calibrando giroscopio)...")
suma, n = np.zeros(3), 0
while n < 200:
    for m in leer_muestras():
        suma += m[4:7]
        n += 1
sesgo = suma / n
print("Listo. Gestos: saludo lateral = 'Hola', bajar la palma = 'Yo soy ...'")

q = np.array([1.0, 0, 0, 0])
hola, baja = DetectorHola(), DetectorBajada()
t_prev, t_hola, t_dbg = None, -1e9, 0.0
pico = np.zeros(3)

while True:
    for t_ms, ax, ay, az, gx, gy, gz in leer_muestras():
        t = t_ms / 1000.0
        g = np.array([gx, gy, gz]) - sesgo
        if t_prev is not None and 0 < t - t_prev < 0.5:
            q = actualizar(q, np.array([ax, ay, az]), np.radians(g), t - t_prev)
            elev = elevacion_deg(q, HAND_FWD)
            if hola.actualizar(t, g):
                t_hola = t
                decir("Hola")
            if baja.actualizar(t, elev) and t - t_hola > 1.0:   # ignora rebotes del saludo
                decir(f"Yo soy {NOMBRE}")
            if DEBUG:
                pico = np.maximum(pico, np.abs(g))
                if t - t_dbg > 1.0:
                    print(f"elev={elev:6.1f} deg | pico gyro x,y,z = {pico.round(0)}")
                    pico[:] = 0
                    t_dbg = t
        t_prev = t
    time.sleep(0.002)
