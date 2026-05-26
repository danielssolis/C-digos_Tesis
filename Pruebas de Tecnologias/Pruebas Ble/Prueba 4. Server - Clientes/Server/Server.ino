#include <NimBLEDevice.h>

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// Callbacks para conexión/desconexión
class ServerCallbacks : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer* pServer) override {
    Serial.println("✅ Cliente conectado");
  }
  void onDisconnect(NimBLEServer* pServer) override {
    Serial.println("❌ Cliente desconectado");
    pServer->startAdvertising();  // Seguir anunciando
  }
};

// Callback para manejar escrituras (recibe mensajes con CLIENT_ID)
class MyCallbacks : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* pCharacteristic) override {
    std::string v = pCharacteristic->getValue();
    String msg = String(v.c_str());
    Serial.print("📥 Datos recibidos: ");
    Serial.println(msg);
  }
};

void setup() {
  Serial.begin(115200);
  Serial.println("🔧 Iniciando servidor BLE...");

  NimBLEDevice::init("ServidorBLE");
  NimBLEServer* pServer = NimBLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());

  NimBLEService* srv = pServer->createService(SERVICE_UUID);
  NimBLECharacteristic* ch = srv->createCharacteristic(
    CHARACTERISTIC_UUID,
    NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE
  );
  ch->setCallbacks(new MyCallbacks());
  srv->start();

  NimBLEAdvertising* adv = pServer->getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->start();

  Serial.println("🚀 Servidor listo para múltiples clientes.");
}

void loop() {
  // Todo se gestiona por callbacks
}

