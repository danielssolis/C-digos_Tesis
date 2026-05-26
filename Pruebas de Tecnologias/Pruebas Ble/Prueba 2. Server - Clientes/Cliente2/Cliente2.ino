#include <NimBLEDevice.h>

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

String CLIENT_ID = "Cliente 2";

NimBLEAdvertisedDevice* foundDevice = nullptr;
NimBLERemoteCharacteristic* pChar = nullptr;
NimBLEClient* pClient = nullptr;

class MyAdvertisedDeviceCallbacks : public NimBLEAdvertisedDeviceCallbacks {
  void onResult(NimBLEAdvertisedDevice* advertisedDevice) override {
    Serial.print("🔍 Encontrado: ");
    Serial.println(advertisedDevice->toString().c_str());

    if (advertisedDevice->isAdvertisingService(NimBLEUUID(SERVICE_UUID))) {
      Serial.println("✅ Servidor BLE detectado.");
      foundDevice = new NimBLEAdvertisedDevice(*advertisedDevice);
      NimBLEDevice::getScan()->stop();
    }
  }
};

bool connectToServer() {
  if (!foundDevice) {
    Serial.println("❌ No se encontró servidor BLE.");
    return false;
  }

  pClient = NimBLEDevice::createClient();
  Serial.println("🔌 Intentando conectar...");

  if (!pClient->connect(foundDevice)) {
    Serial.println("❌ No se pudo conectar al servidor.");
    NimBLEDevice::deleteClient(pClient);
    return false;
  }

  Serial.println("✅ Conectado al servidor BLE");

  NimBLERemoteService* pService = pClient->getService(SERVICE_UUID);
  if (!pService) {
    Serial.println("❌ Servicio no encontrado");
    pClient->disconnect();
    return false;
  }

  pChar = pService->getCharacteristic(CHARACTERISTIC_UUID);
  if (!pChar || !pChar->canWrite()) {
    Serial.println("❌ Característica no válida");
    pClient->disconnect();
    return false;
  }

  return true;
}

void setup() {
  Serial.begin(115200);
  Serial.println("🚀 Iniciando cliente BLE");

  NimBLEDevice::init("");
  NimBLEScan* pScan = NimBLEDevice::getScan();

  pScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pScan->setActiveScan(true);
  pScan->setInterval(45);
  pScan->setWindow(15);

  Serial.println("🔎 Escaneando dispositivos...");
  pScan->start(5, false);

  while (pScan->isScanning()) {
    delay(100);
  }

  if (!connectToServer()) {
    Serial.println("❌ Conexión fallida. Fin del programa.");
  }
}

void loop() {
  if (pClient && pClient->isConnected() && pChar) {
    float temp = random(200, 300) / 10.0;
    float hum = random(400, 700) / 10.0;

    String data = CLIENT_ID + " - Temp: " + String(temp, 1) + " °C, Hum: " + String(hum, 1) + " %";
    pChar->writeValue(data.c_str());
    Serial.println("📤 Enviado: " + data);
  } else {
    Serial.println("⚠️ Cliente no conectado.");
  }

  delay(1000);
}
