#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>

Adafruit_BNO055 bno = Adafruit_BNO055(55);

void setup() {
  Serial.begin(9600);
  delay(1000);

  if (!bno.begin()) {
    Serial.println("BNO055 not detected");
    while (1);
  }

  delay(1000);
  bno.setExtCrystalUse(true);
}

void loop() {
  imu::Vector<3> euler = bno.getVector(Adafruit_BNO055::VECTOR_EULER);

  Serial.print(euler.x());
  Serial.print(",");
  Serial.print(euler.y());
  Serial.print(",");
  Serial.println(euler.z());

  delay(100);
}