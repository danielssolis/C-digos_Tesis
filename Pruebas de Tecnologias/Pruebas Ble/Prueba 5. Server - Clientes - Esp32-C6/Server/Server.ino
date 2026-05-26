#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>

static BLEUUID serviceUUID("12345678-1234-1234-1234-1234567890ab");
static BLEUUID characteristicUUID("87654321-4321-4321-4321-abcdefabcdef");

BLECharacteristic* pCharacteristic;

class MyCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* pCharacteristic) override {
    std::string value = pCharacteristic->getValue();
    if (value.length() > 0) {
      Serial.print("Dato recibido: ");
      Serial.println(value.c_str());
    }
  }
};

void setup() {
  Serial.begin(115200);
  BLEDevice::init("ESP32-C6-Servidor");

  BLEServer* pServer = BLEDevice::createServer();
  BLEService* pService = pServer->createService(serviceUUID);

  pCharacteristic = pService->createCharacteristic(
    characteristicUUID,
    BLECharacteristic::PROPERTY_WRITE
  );
  pCharacteristic->setCallbacks(new MyCallbacks());

  pService->start();
  BLEAdvertising* pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(serviceUUID);
  pAdvertising->start();

  Serial.println("Servidor BLE iniciado. Esperando conexión...");
}

void loop() {
  delay(1000); // No hace nada en el loop
}

Serial.println(BLEDevice::getAddress().toString().c_str());

