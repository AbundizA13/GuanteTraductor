"""Visualizacion 3D minima: una mano que sigue la orientacion del reloj (solo IMU).

Teclas (con la ventana del navegador enfocada):  z = recentrar direccion horizontal,
i = invertir arriba/abajo.  La escena se abre en el navegador (http://localhost:9020).
"""
import math, time, warnings
import numpy as np
import serial

warnings.filterwarnings("ignore", category=UserWarning, module="vpython")
from vpython import canvas, vector, box, compound, color, rate

from fusion import actualizar, matriz

PUERTO, BAUD = "COM5", 115200
HAND_FWD = np.array([0.0, -1.0, 0.0])   # direccion de los dedos en ejes del chip
HAND_UP = np.array([0.0, 0.0, 1.0])     # dorso de la mano (sale de la pantalla del reloj)

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


scene = canvas(title="Mano (solo IMU). z = centrar, i = invertir arriba/abajo",
               width=900, height=600, background=color.gray(0.15))
scene.camera.pos = vector(0, 1.5, 3.5)
scene.camera.axis = vector(0, -1.5, -3.5)

partes = [box(pos=vector(0, 0, 0), size=vector(1.0, 0.2, 1.0), color=color.orange)]
for z in [-0.36, -0.12, 0.12, 0.36]:
    partes.append(box(pos=vector(0.85, 0, z), size=vector(0.7, 0.14, 0.18), color=color.orange))
partes.append(box(pos=vector(0.1, 0, 0.7), size=vector(0.5, 0.14, 0.18), color=color.orange))
mano = compound(partes)


def a_vpython(v):
    # mundo (x, y, z=arriba) -> vpython (x, y=arriba, z)
    return vector(v[0], v[2], -v[1])


q = np.array([1.0, 0, 0, 0])
yaw0 = 0.0


def Rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def orientar(q):
    R = Rz(-yaw0) @ matriz(q)
    mano.axis = a_vpython(R @ HAND_FWD)
    mano.up = a_vpython(R @ HAND_UP)


def tecla(ev):
    global yaw0, HAND_FWD
    if ev.key == "i":
        HAND_FWD = -HAND_FWD
    if ev.key in ("z", "i"):
        f = matriz(q) @ HAND_FWD
        yaw0 = math.atan2(f[1], f[0])


scene.bind("keydown", tecla)

print("Deja el reloj QUIETO 2 s (calibrando giroscopio)...")
suma, n = np.zeros(3), 0
while n < 200:
    for m in leer_muestras():
        suma += m[4:7]
        n += 1
sesgo = suma / n
print("Sesgo:", sesgo)

t_prev = None
while True:
    rate(200)
    for t_ms, ax, ay, az, gx, gy, gz in leer_muestras():
        t = t_ms / 1000.0
        g = np.radians(np.array([gx, gy, gz]) - sesgo)
        if t_prev is not None and 0 < t - t_prev < 0.5:
            q = actualizar(q, np.array([ax, ay, az]), g, t - t_prev)
        t_prev = t
    orientar(q)
