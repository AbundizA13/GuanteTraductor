// Waveshare ESP32-S3-Touch-AMOLED-2.06 : lee el IMU QMI8658C y transmite por USB (Serial)
// Formato de salida, ~100 lineas/s:   millis,ax,ay,az,gx,gy,gz
//   ax..az en g   |   gx..gz en grados/s
// Requiere en Arduino IDE: USB CDC On Boot = Enabled (ver README).
#include <Wire.h>

#define SDA_PIN 15
#define SCL_PIN 14

uint8_t qmiAddr = 0;   // se detecta solo: 0x6B (esperada) o 0x6A

bool leer(uint8_t addr, uint8_t reg, uint8_t* buf, uint8_t n) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, n) != n) return false;
  for (uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}

void escribir(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}

bool detectarIMU() {
  const uint8_t candidatas[] = {0x6B, 0x6A};
  for (uint8_t a : candidatas) {
    uint8_t id = 0;
    if (leer(a, 0x00, &id, 1) && id == 0x05) { qmiAddr = a; return true; }
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  unsigned long t0 = millis();
  while (!Serial && millis() - t0 < 5000) delay(10);   // espera maxima 5 s
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);

  if (detectarIMU()) {
    escribir(qmiAddr, 0x02, 0x40);   // CTRL1: auto-incremento de direccion
    escribir(qmiAddr, 0x03, 0x16);   // CTRL2: acelerometro +-4 g, 125 Hz
    escribir(qmiAddr, 0x04, 0x56);   // CTRL3: giroscopio +-512 dps, 125 Hz
    escribir(qmiAddr, 0x08, 0x03);   // CTRL7: habilitar acelerometro + giroscopio
    delay(50);
  }
}

void loop() {
  if (qmiAddr == 0) {                       // sin IMU: avisa (el lector Python ignora esta linea)
    Serial.println("# IMU no detectado en 0x6B ni 0x6A");
    delay(1000);
    return;
  }
  uint8_t b[12];
  if (!leer(qmiAddr, 0x35, b, 12)) { delay(10); return; }

  int16_t ax = (int16_t)(b[1]  << 8 | b[0]);
  int16_t ay = (int16_t)(b[3]  << 8 | b[2]);
  int16_t az = (int16_t)(b[5]  << 8 | b[4]);
  int16_t gx = (int16_t)(b[7]  << 8 | b[6]);
  int16_t gy = (int16_t)(b[9]  << 8 | b[8]);
  int16_t gz = (int16_t)(b[11] << 8 | b[10]);

  Serial.printf("%lu,%.4f,%.4f,%.4f,%.3f,%.3f,%.3f\n", millis(),
                ax / 8192.0, ay / 8192.0, az / 8192.0,     // +-4 g   -> 8192 LSB/g
                gx / 64.0,   gy / 64.0,   gz / 64.0);      // +-512 dps -> 64 LSB/dps
  delay(10);
}
