# Guante/reloj de gestos con IMU (Waveshare ESP32-S3-Touch-AMOLED-2.06)

Traductor de gestos a palabras. Esta etapa usa **solo el IMU del reloj** (sin sensores flex todavía).
Objetivo inmediato: detectar dos gestos y "decir" palabras:

| Gesto | Palabra |
|---|---|
| Mano de un lado a otro (saludo) | **"Hola"** |
| Palma bajando rápido hacia el pecho | **"Yo soy \<nombre\>"** |

Este documento reúne lo que se necesita saber de la placa (pines, chips, trampas de configuración) para no
tener que volver a buscarlo en wikis, y explica qué funciona, qué está sin probar y cómo continuar.

> **Cómo leer el estado.** Cada dato lleva una etiqueta: **[probado]** = se ejecutó en el hardware real durante
> el desarrollo; **[esquemático/wiki]** = sale de documentación oficial, no se comprobó en el reloj;
> **[simulado]** = se probó solo con datos sintéticos; **[sin verificar]** = memoria o inferencia.

---

## 1. Estado del proyecto

| Pieza | Estado |
|---|---|
| Subir sketches desde Arduino IDE y ver Serial | [probado] (requiere USB CDC On Boot = Enabled) |
| Lectura del QMI8658C (acelerómetro + giroscopio) | [probado] el bus responde y el sesgo del giroscopio se calibra con datos reales |
| Firmware que transmite CSV por USB | `firmware/imu_stream/imu_stream.ino` |
| Fusión de sensores (orientación con cuaterniones) | [probado en parte] la mano 3D respondía al reloj; los signos de los ejes dependen de cómo se porte el reloj (sección 7) |
| Visualización 3D de la mano (vpython) | [probado] `python/demo_mano_3d.py` (se abre en el navegador, versión de referencia) |
| Detectores de "Hola" y "Yo soy" | [simulado] pasan pruebas con datos sintéticos; **falta ajustar umbrales con el reloj puesto** |
| Voz (texto a voz) | [sin verificar] `pyttsx3` opcional |
| Flex de los dedos | pendiente (ver sección 10) |

## 2. Estructura

```
firmware/imu_stream/imu_stream.ino   Lee el IMU y manda "millis,ax,ay,az,gx,gy,gz" ~100 veces/s
python/fusion.py                     Filtro tipo Mahony (cuaterniones) + elevación de los dedos
python/gestos.py                     DetectorHola y DetectorBajada
python/reconocer_gestos.py           Programa principal: lee USB, detecta gestos, imprime/dice palabras
python/demo_mano_3d.py               Mano 3D en el navegador para validar ejes y orientación
python/test_sim.py                   Pruebas con datos simulados (no requiere hardware)
```

Flujo: `reloj (ESP32-S3) --USB serie--> Python (fusión + gestos) --> palabra`.
Toda la matemática está en Python a propósito: se itera sin volver a subir código al reloj.

---

## 3. La placa

**Waveshare ESP32-S3-Touch-AMOLED-2.06**: reloj de muñeca con pantalla AMOLED táctil de 2.06".
Documentación oficial: <https://docs.waveshare.com/ESP32-S3-Touch-AMOLED-2.06>
(espejo <https://www.waveshare.com/wiki/ESP32-S3-Touch-AMOLED-2.06>) · demos:
<https://github.com/waveshareteam/ESP32-S3-Touch-AMOLED-2.06>.

- SoC **ESP32-S3R8**: 8 MB de PSRAM octal. Un solo puerto **USB-C** conectado al USB nativo del chip
  (no hay chip puente USB-UART). [esquemático/wiki]
- Flash **GD25Q256 = 32 MB** según el esquemático, pero las demos de Waveshare compilan con **16 MB**;
  usa 16 MB en Arduino. [esquemático/wiki]
- Periféricos: pantalla CO5300 (410×502, QSPI), touch FT3168, IMU QMI8658C, PMIC AXP2101,
  RTC PCF85063, códecs de audio ES8311/ES7210, ranura microSD, motor de vibración. [esquemático/wiki]

### 3.1 Bus I2C compartido

IMU, PMIC, RTC, códecs y touch cuelgan del **mismo bus**:

| Señal | GPIO | Estado |
|---|---|---|
| **SDA** | **15** | [probado] `Wire.begin(15, 14)` funciona con el IMU |
| **SCL** | **14** | [probado] |

Direcciones I2C:

| Chip | Dirección | Estado |
|---|---|---|
| **QMI8658C (IMU)** | **0x6B** (0x6A como alternativa) | [probado] el firmware prueba ambas y usa la que responda (WHO_AM_I = 0x05) |
| FT3168 (touch) | 0x38 | [esquemático/wiki] |
| AXP2101 (PMIC) | 0x34 | [sin verificar] |
| PCF85063 (RTC) | 0x51 | [sin verificar] |
| ES8311 (códec) | 0x18 | [sin verificar] |

### 3.2 Otros pines

Estos pines vienen del esquemático V1.0 y de la wiki. **No se cotejaron con `pin_config.h`** del repo
(no se pudo descargar): verifícalos ahí antes de depender de ellos.

| Función | GPIO |
|---|---|
| Pantalla QSPI datos SIO0–SIO3 | 4, 5, 6, 7 |
| Pantalla SCLK / CS / TE / RESET | 11 / 12 / 13 / 8 |
| Touch INT / RST | 38 / 9 |
| IMU INT1 (INT2 no está ruteada) | 21 |
| RTC INT | 39 |
| microSD MOSI / SCK / MISO / CS | 1 / 2 / 3 / 17 |
| Motor de vibración | 18 |
| Amplificador de audio (PA_CTRL) | 46 |
| Lectura del botón PWR (vía MOSFET, alto = pulsado) | 10 |
| BOOT | 0 (bajo = pulsado) |

**No uses GPIO26–37 en tus sketches.** Están ocupados por la flash y la PSRAM octal.
El GPIO35 además es la línea de interrupción del AXP2101; reconfigurarlo corrompe el bus de la PSRAM y
congela el firmware (issue #17 del repo de Waveshare).

### 3.3 Botones

- **BOOT (GPIO0):** manténlo pulsado mientras conectas el USB para entrar en **modo descarga** (recuperación).
- **PWR:** va al PMIC AXP2101. Con el reloj apagado, una pulsación corta enciende; **~6 s pulsado** apaga.
  No hay botón de reset dedicado: para reiniciar, apaga con PWR (6 s) y vuelve a encender. [wiki + esquemático]

### 3.4 Firmware de fábrica

Trae una demo multi-app basada en esp-brookesia (DrawPanel, SpecAnalyzer, AIChats, GravitySphere, VideoPlayer,
Gallery, MusicPlayer, Settings). **AIChats** es el asistente de voz **XiaoZhi** (frase "Hello XiaoZhi"):
necesita Wi-Fi de 2.4 GHz, internet y un código de activación de 6 dígitos en xiaozhi.me. [wiki]
No se encontró ninguna fuente que llame "Helen" al asistente ni que reporte un congelamiento a los 20 s;
si aparece en pantalla, anota el texto exacto.

Al subir cualquier sketch el firmware de fábrica se sobrescribe. **Hay un respaldo hecho con esptool** (guárdalo).
Para que el respaldo sea completo debe pesar exactamente 33 554 432 bytes (32 MB):

```
esptool.py --chip esp32s3 --port COM5 read_flash 0x0 0x2000000 respaldo_completo.bin   # respaldar
esptool.py --chip esp32s3 --port COM5 write_flash 0x0 respaldo_completo.bin            # restaurar
esptool.py --chip esp32s3 --port COM5 erase_flash                                      # borrado total
```

(En esptool v5 los comandos se escriben con guiones: `erase-flash`, `read-flash`.) [sin verificar la sintaxis exacta en tu versión]

---

## 4. Arduino IDE: ajustes obligatorios

Placa **ESP32S3 Dev Module**, núcleo esp32 de Espressif 3.2.0 o superior (Waveshare prueba con 3.3.11).

| Ajuste (menú Herramientas) | Valor |
|---|---|
| **USB CDC On Boot** | **Enabled** |
| USB Mode | Hardware CDC and JTAG |
| PSRAM | OPI PSRAM |
| Flash Size | 16MB |
| Partition Scheme | 16M Flash (3MB APP/9.9MB FATFS) |

### Trampas del puerto serie (las que más tiempo hicieron perder)

1. **Con USB CDC On Boot en Disabled, `Serial` sale por un UART que no llega al USB-C**: el monitor solo muestra
   `ESP-ROM:esp32s3-20210327` (el banner de la ROM) y nada más. Es opción de compilación: hay que activar y **volver a subir**.
2. **El puerto COM cambia** tras subir el sketch (el USB se reenumera). Vuelve a seleccionarlo en Herramientas → Puerto.
3. **Solo un programa puede abrir el puerto**: cierra el Monitor Serie de Arduino antes de correr Python.
4. Muchos cables USB-C son solo de carga. Si no aparece ningún puerto COM, cambia el cable.
5. Si no deja subir: modo descarga (mantén BOOT, conecta el USB, suelta).
6. La pantalla **no se actualiza** con un sketch que no la inicializa: sigue mostrando el último cuadro del firmware
   anterior. No indica si tu sketch corre o se colgó.

---

## 5. El IMU QMI8658C

Registros usados (configuración de `imu_stream.ino`):

| Registro | Valor | Significado |
|---|---|---|
| 0x00 `WHO_AM_I` | 0x05 | Identificación del chip |
| 0x02 `CTRL1` | 0x40 | Auto-incremento de dirección |
| 0x03 `CTRL2` | 0x16 | Acelerómetro ±4 g, 125 Hz |
| 0x04 `CTRL3` | 0x56 | Giroscopio ±512 °/s, 125 Hz |
| 0x08 `CTRL7` | 0x03 | Habilitar acelerómetro + giroscopio |
| 0x35 | 12 bytes | AX,AY,AZ,GX,GY,GZ (int16 little-endian, en ese orden) |

Conversión: acelerómetro **8192 LSB/g**, giroscopio **64 LSB/(°/s)**. Es un IMU de **6 ejes** (sin magnetómetro).

- **Acelerómetro** = fuerza que siente el chip, incluida la gravedad (~1 g total en reposo). Da la **inclinación**.
- **Giroscopio** = **velocidad de giro** (°/s). En reposo ~0 pero con sesgo de unos pocos °/s: se calibra al arrancar.

### Protocolo USB

Una línea de texto por muestra, ~100 por segundo, 115200 baudios:

```
millis,ax,ay,az,gx,gy,gz
```

Las líneas que empiezan con `#` o no tienen 7 campos numéricos son diagnóstico y el lector Python las descarta.

---

## 6. Entorno Python (Windows / PyCharm)

```
python -m pip install pyserial numpy vpython "setuptools<81" pyttsx3
```

Problemas encontrados y sus soluciones:

- **Usa siempre `python -m pip ...`**, no `pip`. En un proyecto dentro de OneDrive con espacios o "ñ" en la ruta,
  `pip.exe` del `.venv` falla con "El sistema no puede encontrar el archivo especificado".
  Mejor aún: crea el proyecto y el `.venv` en una ruta corta sin OneDrive (`C:\proyectos\guante`).
- **`ModuleNotFoundError: No module named 'pkg_resources'`** al importar vpython: `python -m pip install "setuptools<81"`.
  El aviso posterior de "pkg_resources is deprecated" es inofensivo.
- El paquete es **`pyserial`**, no `serial` (si instalaste `serial`, desinstálalo: chocan).
- **vpython no abre ventana propia**: sirve la escena en el navegador. Si PyCharm no lo abre, entra a
  <http://localhost:9020> mientras el script corre.

---

## 7. Orientación: cómo se obtiene y qué limita

`python/fusion.py` implementa un filtro tipo Mahony con **cuaterniones**: el giroscopio da los cambios rápidos y
el acelerómetro corrige la deriva usando la gravedad. Se usan cuaterniones porque el enfoque anterior con ángulos
roll/pitch por separado hace que la mano virtual "se vuelva loca" al rotar la muñeca ~90° (bloqueo de cardán).

Ejes y montaje: el reloj va en el dorso de la muñeca. `HAND_FWD` es el **vector, en ejes del chip, que apunta hacia
los dedos**; `HAND_UP` sale de la pantalla del reloj (dorso de la mano). Para validarlos:

1. Corre `demo_mano_3d.py`, con el reloj puesto y la mano en posición neutra presiona **z** (centra la dirección horizontal).
2. Sube y baja la palma: debe subir y bajar la mano virtual. Si sale al revés, presiona **i** (invierte el signo de `HAND_FWD`).
3. Si el giro de la muñeca sale al revés, prueba `HAND_UP = [0, 0, -1]`.
4. Copia el `HAND_FWD` que funcionó a `reconocer_gestos.py` (`HAND_FWD = ...`). **Debe ser el mismo en ambos**.
   Candidatos: `[0,±1,0]` o `[±1,0,0]`.

**Límite conocido:** sin magnetómetro, el giro alrededor del eje vertical (yaw) **se desvía lentamente**.
Roll y pitch son absolutos y estables. Para la visualización se recentra con **z**; los gestos propuestos no dependen del yaw.

---

## 8. Detección de gestos (propuesta)

Dos detectores independientes en `python/gestos.py`. Ambos reciben muestras en orden y devuelven `True` al detectar,
con un tiempo de enfriamiento para no repetir.

### "Hola": `DetectorHola`
El saludo lateral hace que el giroscopio **cambie de signo varias veces**. Se cuentan los cambios de sentido
(con umbral, para ignorar ruido) por cada eje. Si cualquier eje acumula ≥ 3 cambios en 1.6 s, es saludo.
Al mirar los tres ejes no hace falta saber cómo quedó montado el reloj.

| Parámetro | Valor inicial | Efecto |
|---|---|---|
| `umbral_dps` | 90 | Velocidad mínima para contar un movimiento. Súbelo si detecta de más |
| `cambios` | 3 | Vaivenes necesarios (izq-der-izq) |
| `ventana_s` | 1.6 | Tiempo máximo para completarlos |
| `enfriamiento_s` | 2.0 | Pausa tras detectar |

### "Yo soy \<nombre\>": `DetectorBajada`
Usa la **elevación de los dedos** (ángulo respecto a la horizontal, calculado con la orientación fusionada):
si pierden ≥ 30° en ≤ 0.6 s, es una bajada rápida. Depende de `HAND_FWD` correcto (sección 7).

| Parámetro | Valor inicial | Efecto |
|---|---|---|
| `caida_deg` | 30 | Cuánto tiene que bajar |
| `ventana_s` | 0.6 | En cuánto tiempo (más chico = más "rápido") |
| `enfriamiento_s` | 1.5 | Pausa tras detectar |

`reconocer_gestos.py` ignora una "bajada" que ocurra menos de 1 s después de un "Hola", porque el saludo mueve la muñeca.

### Pruebas realizadas ([simulado])
`python/test_sim.py` simula un cuerpo rígido con datos de acelerómetro y giroscopio sintéticos:

| Caso | Resultado |
|---|---|
| Reloj quieto con ruido | no dispara |
| Saludo a 2.5 Hz, ±40° | dispara "Hola" una vez |
| Bajada de 50° en 0.4 s | dispara "Yo soy" una vez |
| Bajada lenta (50° en 3 s) | no dispara |
| Un solo giro de muñeca | no dispara "Hola" |

**Esto no sustituye probar con el reloj puesto.** Los umbrales salen de movimientos idealizados; una persona real
tendrá otra amplitud y velocidad. Usa `python reconocer_gestos.py --debug`: cada segundo imprime la elevación
actual y el pico del giroscopio por eje, para ajustar los umbrales con datos reales.

### Salida de palabras
`decir()` imprime siempre y, si `pyttsx3` está instalado, además habla (voz offline del sistema; en Windows usa las
voces instaladas, para español hay que tener una voz en español). Alternativas: `gTTS` (necesita internet),
o mandar la palabra a una interfaz web. Cambia `NOMBRE` en `reconocer_gestos.py`.

---

## 9. Ejecución rápida

1. Arduino IDE: ajustes de la sección 4, abre `firmware/imu_stream/imu_stream.ino`, sube.
2. Cierra el Monitor Serie y anota el puerto COM.
3. Edita `PUERTO`, `NOMBRE` y `HAND_FWD` en `python/reconocer_gestos.py` (y `PUERTO` en `demo_mano_3d.py`).
4. `python demo_mano_3d.py` → valida ejes (sección 7).
5. `python reconocer_gestos.py --debug` → prueba los gestos y ajusta umbrales.

Verificación de firmware sin Python: Monitor Serie a 115200 debe mostrar líneas `123456,0.01,-0.02,1.00,0.5,-0.3,0.1`.
Con el reloj quieto, la magnitud de (ax,ay,az) es ~1 y el giroscopio ~0.

## 10. Siguientes pasos

1. Ajustar umbrales con el reloj puesto y con varias personas.
2. Agregar los **sensores flex** (5 dedos): divisor de voltaje con Rf ≈ 22 kΩ, pines ADC1, calibración mín/máx por dedo,
   valores normalizados 0–1. Los pines de la placa ocupados están en la sección 3.2; hay que elegir GPIO libres
   y confirmarlos contra `pin_config.h`.
3. Cuando haya más de 3–4 gestos, cambiar las reglas por un clasificador: grabar ventanas de 1–2 s
   (aceleración, giroscopio, flex) etiquetadas, extraer características o usar una CNN 1D pequeña, y evaluar con
   validación por persona.
4. Mostrar la palabra también en la pantalla del reloj (requiere inicializar el CO5300 por QSPI; punto de partida:
   ejemplo oficial `04_LVGL_QMI8658_ui`).

## Fuentes
- Wiki oficial: <https://docs.waveshare.com/ESP32-S3-Touch-AMOLED-2.06> · <https://www.waveshare.com/wiki/ESP32-S3-Touch-AMOLED-2.06>
- Demos y esquemático: <https://github.com/waveshareteam/ESP32-S3-Touch-AMOLED-2.06> (issue #17: GPIO35, PSRAM y AXP2101)
- Factory firmware: <https://docs.waveshare.com/ESP32-S3-Touch-AMOLED-2.06/Instructions-For-Use>
- SensorLib (direcciones del QMI8658): <https://github.com/lewisxhe/SensorLib>
- USB CDC en Arduino-ESP32: <https://docs.espressif.com/projects/arduino-esp32/en/latest/api/usb_cdc.html>
