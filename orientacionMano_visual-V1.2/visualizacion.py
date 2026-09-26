import time, math
import numpy as np
import serial
from vpython import canvas, vector, box, compound, color, rate

PUERTO = "COM11"        # <-- cambia esto
BAUD   = 115200
ALPHA  = 0.98          # confianza en el giroscopio

# ---------- Paso 3: puerto serie ----------
ser = serial.Serial(PUERTO, BAUD, timeout=0.01)
time.sleep(1.5)
ser.reset_input_buffer()

def leer_muestras():
    """Devuelve todas las muestras pendientes como listas de 7 floats."""
    out = []
    while ser.in_waiting:
        try:
            partes = ser.readline().decode(errors="ignore").strip().split(",")
            if len(partes) == 7:
                out.append([float(p) for p in partes])
        except ValueError:
            pass
    return out

# ---------- Paso 6: modelo de la mano ----------
scene = canvas(title="Mano (solo IMU). Tecla 'z' = poner cero",
               width=900, height=600, background=color.gray(0.15))
scene.camera.pos = vector(0, 1.5, 3.5)
scene.camera.axis = vector(0, -1.5, -3.5)

partes = [box(pos=vector(0, 0, 0), size=vector(1.0, 0.2, 1.0), color=color.orange)]
for i, z in enumerate([-0.36, -0.12, 0.12, 0.36]):
    partes.append(box(pos=vector(0.85, 0, z), size=vector(0.7, 0.14, 0.18), color=color.orange))
partes.append(box(pos=vector(0.1, 0, 0.7), size=vector(0.5, 0.14, 0.18), color=color.orange))  # pulgar
mano = compound(partes)

# ---------- Paso 7: rotacion ----------
# ---------- Orientacion con cuaterniones ----------
HAND_FWD = np.array([0.0, -1.0, 0.0])   # hacia donde apuntan los dedos, en ejes del chip
HAND_UP  = np.array([0.0, 0.0, 1.0])   # dorso de la mano = saliendo de la pantalla del reloj
KP = 2.0                               # cuanto se confia en el acelerometro

q = np.array([1.0, 0.0, 0.0, 0.0])
yaw0 = 0.0

def actualizar(q, a, g, dt):
    """a en g, g en rad/s. Devuelve el cuaternion actualizado."""
    n = np.linalg.norm(a)
    w, x, y, z = q
    if n > 1e-6:
        a = a / n
        v = np.array([2*(x*z - w*y), 2*(w*x + y*z), w*w - x*x - y*y + z*z])
        g = g + KP * np.cross(a, v)
    gx, gy, gz = g
    dq = 0.5 * np.array([-x*gx - y*gy - z*gz,
                          w*gx + y*gz - z*gy,
                          w*gy - x*gz + z*gx,
                          w*gz + x*gy - y*gx])
    q = q + dq * dt
    return q / np.linalg.norm(q)

def matriz(q):
    w, x, y, z = q
    return np.array([
        [1-2*(y*y+z*z), 2*(x*y-w*z),   2*(x*z+w*y)],
        [2*(x*y+w*z),   1-2*(x*x+z*z), 2*(y*z-w*x)],
        [2*(x*z-w*y),   2*(y*z+w*x),   1-2*(x*x+y*y)]])

def Rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

def orientar(q):
    R = Rz(-yaw0) @ matriz(q)
    mano.axis = a_vpython(R @ HAND_FWD)
    mano.up   = a_vpython(R @ HAND_UP)

def tecla(ev):
    global yaw0
    if ev.key == "z":                      # recentra la direccion horizontal
        f = matriz(q) @ HAND_FWD
        yaw0 = math.atan2(f[1], f[0])
scene.bind("keydown", tecla)


def a_vpython(v):
    # ejes del chip (x,y,z) -> ejes de vpython (x,y,z), con y hacia arriba.
    # Si algo se mueve al reves, cambia signos o intercambia ejes aqui.
    return vector(v[0], v[2], -v[1])



# ---------- Paso 4: sesgo del giroscopio ----------
print("Deja el reloj QUIETO... calibrando giroscopio")
suma, n = np.zeros(3), 0
while n < 200:
    for m in leer_muestras():
        suma += m[4:7]; n += 1
sesgo = suma / n
print("Sesgo:", sesgo)

# ---------- Paso 5: filtro complementario ----------
t_prev = None
while True:
    rate(200)
    for t, ax, ay, az, gx, gy, gz in leer_muestras():
        g = np.radians([gx - sesgo[0], gy - sesgo[1], gz - sesgo[2]])
        if t_prev is not None:
            dt = (t - t_prev) / 1000.0
            if 0 < dt < 0.5:
                q = actualizar(q, np.array([ax, ay, az]), g, dt)
        t_prev = t
    orientar(q)