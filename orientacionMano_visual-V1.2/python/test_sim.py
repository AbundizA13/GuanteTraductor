import math, numpy as np
from fusion import actualizar, matriz, elevacion_deg
from gestos import DetectorHola, DetectorBajada

FWD = np.array([0.0, 1.0, 0.0])
DT = 0.01

def simular(omega_fn, T, sesgo=(0,0,0)):
    """Cuerpo rigido: q_real evoluciona con omega (deg/s, ejes del chip). Devuelve muestras."""
    q_real = np.array([1.0,0,0,0]); out=[]
    for k in range(int(T/DT)):
        t=k*DT; w=np.array(omega_fn(t)); 
        # integrar rotacion real
        wx,wy,wz=np.radians(w); x,y,z=q_real[1:]; ww=q_real[0]
        dq=0.5*np.array([-x*wx-y*wy-z*wz, ww*wx+y*wz-z*wy, ww*wy-x*wz+z*wx, ww*wz+x*wy-y*wx])
        q_real=q_real+dq*DT; q_real/=np.linalg.norm(q_real)
        a = matriz(q_real).T @ np.array([0,0,1.0])      # gravedad en ejes del chip
        out.append((t, a, w+np.array(sesgo)))
    return out

def correr(muestras):
    q=np.array([1.0,0,0,0]); hola=DetectorHola(); baja=DetectorBajada(); ev=[]
    for t,a,g in muestras:
        q=actualizar(q,a,np.radians(g),DT)
        if hola.actualizar(t,g): ev.append((round(t,2),'HOLA'))
        if baja.actualizar(t,elevacion_deg(q,FWD)): ev.append((round(t,2),'BAJADA'))
    return ev, elevacion_deg(q,FWD)

# 1) quieto con ruido pequeno -> nada
rng=np.random.default_rng(0)
m=[(t,a+rng.normal(0,0.01,3),g+rng.normal(0,2,3)) for t,a,g in simular(lambda t:(0,0,0),5)]
print("quieto:", correr(m))
# 2) saludo: oscila 2.5 Hz sobre eje z, +-40 grados de amplitud
w=2*math.pi*2.5; A=40
m=simular(lambda t:(0,0,math.degrees(A*math.pi/180*w*math.cos(w*t))) if t<1.5 else (0,0,0),4)
print("saludo eje z:", correr(m))
# 3) bajada: dedos pierden 50 grados en 0.4 s (rotacion sobre x, sentido negativo)
m=simular(lambda t:(-125,0,0) if 1.0<t<1.4 else (0,0,0),3)
print("bajada:", correr(m))
# 4) subida lenta y bajada lenta (no debe disparar): 50 grados en 3 s
m=simular(lambda t:(-17,0,0) if 1.0<t<4.0 else (0,0,0),6)
print("bajada lenta (no debe disparar):", correr(m))
# 5) giro de muñeca sobre el eje de los dedos (y), una sola vez -> no debe disparar hola
m=simular(lambda t:(0,150,0) if 1.0<t<1.6 else (0,0,0),3)
print("giro muneca 1 vez:", correr(m))
