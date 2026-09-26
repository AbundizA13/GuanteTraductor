"""Configuracion compartida por todos los scripts (un solo lugar para no desincronizarlos)."""
import numpy as np

PUERTO = "COM5"   # el puerto que veas en Administrador de dispositivos
BAUD = 115200

# Direccion de los dedos en ejes del chip. Validala con demo_mano_3d.py: la tecla 'i'
# invierte el signo e imprime la linea exacta para pegar aqui.
HAND_FWD = np.array([0.0, -1.0, 0.0])
HAND_UP = np.array([0.0, 0.0, 1.0])      # dorso de la mano (sale de la pantalla del reloj)
