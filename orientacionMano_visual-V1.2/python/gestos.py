"""Detectores de gestos. Cada uno recibe muestras en orden y devuelve True al detectar."""
from collections import deque


class DetectorHola:
    """Saludo: la mano oscila de lado a lado -> el giroscopio cambia de signo varias veces.

    Cuenta cambios de sentido (con umbral, para ignorar ruido) por eje, en una ventana corta.
    Si cualquier eje acumula `cambios` cambios dentro de `ventana_s`, hay saludo.
    """

    def __init__(self, umbral_dps=90.0, cambios=3, ventana_s=1.6, enfriamiento_s=2.0):
        self.umbral = umbral_dps
        self.cambios = cambios
        self.ventana = ventana_s
        self.enfriamiento = enfriamiento_s
        self._reset()
        self.t_ultimo = -1e9

    def _reset(self):
        self.signo = [0, 0, 0]
        self.eventos = [deque(), deque(), deque()]

    def actualizar(self, t, g):
        """t en segundos; g = (gx, gy, gz) en grados/s, ya sin sesgo."""
        if t - self.t_ultimo < self.enfriamiento:
            return False
        for i in range(3):
            s = 1 if g[i] > self.umbral else (-1 if g[i] < -self.umbral else 0)
            if s != 0 and s != self.signo[i]:
                if self.signo[i] != 0:
                    self.eventos[i].append(t)
                self.signo[i] = s
            while self.eventos[i] and t - self.eventos[i][0] > self.ventana:
                self.eventos[i].popleft()
            if len(self.eventos[i]) >= self.cambios:
                self.t_ultimo = t
                self._reset()
                return True
        return False


class DetectorBajada:
    """Palma bajando rapido: los dedos pierden `caida_deg` de elevacion en `ventana_s`."""

    def __init__(self, caida_deg=30.0, ventana_s=0.6, enfriamiento_s=1.5):
        self.caida = caida_deg
        self.ventana = ventana_s
        self.enfriamiento = enfriamiento_s
        self.hist = deque()
        self.t_ultimo = -1e9

    def actualizar(self, t, elev_deg):
        self.hist.append((t, elev_deg))
        while self.hist and t - self.hist[0][0] > self.ventana:
            self.hist.popleft()
        if t - self.t_ultimo < self.enfriamiento:
            return False
        if max(e for _, e in self.hist) - elev_deg >= self.caida:
            self.t_ultimo = t
            self.hist.clear()
            return True
        return False
