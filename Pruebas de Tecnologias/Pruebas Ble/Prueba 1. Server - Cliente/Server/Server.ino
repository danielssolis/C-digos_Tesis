#include <NimBLEDevice.h>

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

class MyCallbacks : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* pCharacteristic) override {
    std::string value = pCharacteristic->getValue();
    Serial.print("📥 Datos recibidos: ");
    Serial.println(value.c_str());
  }
};

void setup() {
  Serial.begin(115200);
  Serial.println("🔧 Iniciando servidor BLE...");

  NimBLEDevice::init("ServidorBLE");

  NimBLEServer* pServer = NimBLEDevice::createServer();
  NimBLEService* pService = pServer->createService(SERVICE_UUID);

  NimBLECharacteristic* pCharacteristic = pService->createCharacteristic(
    CHARACTERISTIC_UUID,
    NIMBLE_PROPERTY::READ |
    NIMBLE_PROPERTY::WRITE
  );

  pCharacteristic->setCallbacks(new MyCallbacks());
  pCharacteristic->setValue("Esperando datos...");
  pService->start();

  NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->start();

  Serial.println("🚀 Servidor BLE iniciado. Esperando cliente...");
}

void loop() {
  // Nada en el loop, espera mensajes del cliente
}

