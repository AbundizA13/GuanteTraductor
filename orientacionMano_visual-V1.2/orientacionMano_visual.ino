#include <Wire.h>

#define SDA_PIN 15
#define SCL_PIN 14

uint8_t qmiAddr = 0;

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

void escanear() {
  Serial.println("--- Escaneo I2C (SDA=15, SCL=14) ---");
  int n = 0;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  dispositivo en 0x%02X\n", a);
      n++;
    }
  }
  if (n == 0) Serial.println("  no respondio nada");
}

bool detectarIMU() {
  const uint8_t candidatas[] = {0x6B, 0x6A};
  for (uint8_t a : candidatas) {
    uint8_t id = 0;
    if (leer(a, 0x00, &id, 1)) {
      Serial.printf("0x%02X responde, WHO_AM_I = 0x%02X %s\n", a, id,
                    id == 0x05 ? "-> QMI8658C detectado" : "-> no es el QMI8658");
      if (id == 0x05) { qmiAddr = a; return true; }
    }
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  unsigned long t0 = millis();
  while (!Serial && millis() - t0 < 5000) delay(10);   // espera maxima 5 s
  delay(500);

  Serial.println("\n=== Deteccion del IMU ===");
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);

  escanear();

  if (detectarIMU()) {
    escribir(qmiAddr, 0x02, 0x40);   // auto-incremento
    escribir(qmiAddr, 0x03, 0x16);   // accel +-4 g, 125 Hz
    escribir(qmiAddr, 0x04, 0x56);   // gyro +-512 dps, 125 Hz
    escribir(qmiAddr, 0x08, 0x03);   // habilitar accel + gyro
    delay(50);
  }
}

void loop() {
  uint8_t b[12];
  if (!leer(qmiAddr, 0x35, b, 12)) return;   // en tu versión anterior: leer(REG_AX_L, b, 12)

  int16_t ax = (int16_t)(b[1]  << 8 | b[0]);
  int16_t ay = (int16_t)(b[3]  << 8 | b[2]);
  int16_t az = (int16_t)(b[5]  << 8 | b[4]);
  int16_t gx = (int16_t)(b[7]  << 8 | b[6]);
  int16_t gy = (int16_t)(b[9]  << 8 | b[8]);
  int16_t gz = (int16_t)(b[11] << 8 | b[10]);

  Serial.printf("%lu,%.4f,%.4f,%.4f,%.3f,%.3f,%.3f\n", millis(),
                ax / 8192.0, ay / 8192.0, az / 8192.0,
                gx / 64.0, gy / 64.0, gz / 64.0);
  delay(10);
}