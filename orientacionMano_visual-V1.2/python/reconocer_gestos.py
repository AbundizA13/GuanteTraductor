"""Lee el IMU por USB, estima la orientacion y dice palabras al detectar gestos.

Uso:   python reconocer_gestos.py            (Monitor Serie de Arduino CERRADO)
       python reconocer_gestos.py --debug    (imprime elevacion y picos del giroscopio)
"""
import queue, sys, threading, time
import numpy as np
import serial

from fusion import actualizar, elevacion_deg
from gestos import Reconocedor
from config import PUERTO, BAUD, HAND_FWD

# ---------------- CONFIGURACION ----------------
NOMBRE = "TU NOMBRE"                           # para la frase "Yo soy <nombre>"
DEBUG = "--debug" in sys.argv
# (PUERTO y HAND_FWD se cambian en config.py, compartido con demo_mano_3d.py)
# -----------------------------------------------

_frases = queue.Queue()


def _hilo_voz():
    """Habla en segundo plano para no frenar la lectura del puerto serie.

    El motor se crea en este hilo (en Windows SAPI debe usarse desde el hilo que lo creo)
    y se recrea en cada frase: evita el fallo conocido de pyttsx3 que deja de hablar
    despues de la primera llamada a runAndWait().
    """
    import pyttsx3
    try:
        import comtypes                        # Windows: cada hilo que usa SAPI inicializa COM
        comtypes.CoInitialize()
    except ImportError:
        pass
    while True:
        texto = _frases.get()
        try:
            voz = pyttsx3.init()
            voz.say(texto)
            voz.runAndWait()
            voz.stop()
            del voz
        except Exception as e:
            print(f"(voz) error: {e}")


try:
    import pyttsx3                             # voz offline (pip install pyttsx3)
    threading.Thread(target=_hilo_voz, daemon=True).start()
    _hay_voz = True
except ImportError:
    _hay_voz = False
    print("(pyttsx3 no instalado: solo se imprimiran las palabras)")


def decir(texto):
    print(f">>> {texto}")
    if _hay_voz:
        _frases.put(texto)


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
rec = Reconocedor()
t_prev, t_dbg = None, 0.0
pico = np.zeros(3)

while True:
    for t_ms, ax, ay, az, gx, gy, gz in leer_muestras():
        t = t_ms / 1000.0
        g = np.array([gx, gy, gz]) - sesgo
        if t_prev is not None and 0 < t - t_prev < 0.5:
            q = actualizar(q, np.array([ax, ay, az]), np.radians(g), t - t_prev)
            elev = elevacion_deg(q, HAND_FWD)
            gesto = rec.actualizar(t, g, elev)
            if gesto == "hola":
                decir("Hola")
            elif gesto == "bajada":
                decir(f"Yo soy {NOMBRE}")
            if DEBUG:
                pico = np.maximum(pico, np.abs(g))
                if t - t_dbg > 1.0:
                    print(f"elev={elev:6.1f} deg | pico gyro x,y,z = {pico.round(0)}")
                    pico[:] = 0
                    t_dbg = t
        t_prev = t
    time.sleep(0.002)
