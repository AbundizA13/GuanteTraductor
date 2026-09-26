"""Pruebas con datos simulados (no requiere el reloj).  Uso: python test_sim.py"""
import math, sys
import numpy as np
from fusion import actualizar, matriz, elevacion_deg
from gestos import Reconocedor
from config import HAND_FWD

DT = 0.01
# Ejes de giro derivados de HAND_FWD, para que la prueba use el mismo montaje que el programa real
BAJAR = np.cross([0.0, 0.0, 1.0], HAND_FWD)   # girar sobre este eje baja los dedos
VERTICAL = np.array([0.0, 0.0, 1.0])          # saludo: vaiven alrededor de la vertical
MUNECA = HAND_FWD                              # giro de muñeca: alrededor del eje de los dedos


def simular(omega_fn, T):
    """Cuerpo rigido: q_real evoluciona con omega (deg/s, ejes del chip). Devuelve muestras."""
    q_real = np.array([1.0, 0, 0, 0])
    out = []
    for k in range(int(T / DT)):
        t = k * DT
        w = np.array(omega_fn(t), dtype=float)
        wx, wy, wz = np.radians(w)
        ww, x, y, z = q_real
        dq = 0.5 * np.array([-x*wx - y*wy - z*wz, ww*wx + y*wz - z*wy,
                             ww*wy - x*wz + z*wx, ww*wz + x*wy - y*wx])
        q_real = q_real + dq * DT
        q_real /= np.linalg.norm(q_real)
        a = matriz(q_real).T @ np.array([0, 0, 1.0])      # gravedad en ejes del chip
        out.append((t, a, w))
    return out


def correr(muestras):
    q = np.array([1.0, 0, 0, 0])
    rec = Reconocedor()
    ev = []
    for t, a, g in muestras:
        q = actualizar(q, a, np.radians(g), DT)
        gesto = rec.actualizar(t, g, elevacion_deg(q, HAND_FWD))
        if gesto:
            ev.append((round(t, 2), gesto))
    return ev


w_hola = 2 * math.pi * 2.5                                         # 2.5 Hz
saludo = lambda t0: (lambda t: VERTICAL * math.degrees(math.radians(40) * w_hola
                                                       * math.cos(w_hola * (t - t0))))
rng = np.random.default_rng(0)

casos = [
    ("quieto con ruido",
     [(t, a + rng.normal(0, 0.01, 3), g + rng.normal(0, 2, 3))
      for t, a, g in simular(lambda t: (0, 0, 0), 5)], []),
    ("saludo",
     simular(lambda t: saludo(0)(t) if t < 1.5 else (0, 0, 0), 4), ["hola"]),
    ("bajada rapida (50 grados en 0.4 s)",
     simular(lambda t: 125 * BAJAR if 1.0 < t < 1.4 else (0, 0, 0), 3), ["bajada"]),
    ("bajada lenta (50 grados en 3 s)",
     simular(lambda t: 17 * BAJAR if 1.0 < t < 4.0 else (0, 0, 0), 6), []),
    ("giro de muñeca una vez",
     simular(lambda t: 150 * MUNECA if 1.0 < t < 1.6 else (0, 0, 0), 3), []),
    # La mano baja al empezar a saludar: antes sonaba "Yo soy" y luego "Hola".
    ("bajada justo antes de saludar",
     simular(lambda t: 125 * BAJAR if 1.0 < t < 1.3
             else (saludo(1.3)(t) if 1.3 <= t < 2.8 else (0, 0, 0)), 5), ["hola"]),
]

fallos = 0
for nombre, muestras, esperado in casos:
    ev = correr(muestras)
    ok = [g for _, g in ev] == esperado
    fallos += not ok
    print(f"[{'OK' if ok else 'FALLA'}] {nombre}: {ev} (esperado {esperado})")
sys.exit(1 if fallos else 0)
