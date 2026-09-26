"""Orientacion a partir de acelerometro + giroscopio (filtro tipo Mahony, cuaterniones)."""
import math
import numpy as np

KP = 2.0  # cuanto se confia en el acelerometro (sube = corrige mas rapido, mas ruido)


def actualizar(q, a, g_rad, dt, kp=KP):
    """q: cuaternion [w,x,y,z]; a: aceleracion (g); g_rad: giroscopio en rad/s."""
    w, x, y, z = q
    n = np.linalg.norm(a)
    if n > 1e-6:
        a = a / n
        v = np.array([2 * (x * z - w * y), 2 * (w * x + y * z), w * w - x * x - y * y + z * z])
        g_rad = g_rad + kp * np.cross(a, v)
    gx, gy, gz = g_rad
    dq = 0.5 * np.array([-x * gx - y * gy - z * gz,
                          w * gx + y * gz - z * gy,
                          w * gy - x * gz + z * gx,
                          w * gz + x * gy - y * gx])
    q = q + dq * dt
    return q / np.linalg.norm(q)


def matriz(q):
    """Matriz que convierte vectores del chip a vectores del mundo (z = arriba)."""
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def elevacion_deg(q, hand_fwd):
    """Angulo de los dedos respecto a la horizontal: +90 = hacia arriba, -90 = hacia abajo."""
    f = matriz(q) @ hand_fwd
    return math.degrees(math.asin(max(-1.0, min(1.0, f[2]))))
