#include <NimBLEDevice.h>

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

String CLIENT_ID = "Cliente 1";  // Ajusta en cada ESP32: "Cliente 1", "Cliente 2" o "Cliente 3"

NimBLEClient*        pClient = nullptr;
NimBLERemoteCharacteristic* pChar = nullptr;

bool connectToServer() {
  NimBLEScan* scan = NimBLEDevice::getScan();
  scan->setActiveScan(true);
  NimBLEScanResults results = scan->start(5, false);
  scan->clearResults();

  NimBLEUUID svcUUID(SERVICE_UUID);
  for (int i = 0; i < results.getCount(); i++) {
    NimBLEAdvertisedDevice dev = results.getDevice(i);
    if (dev.isAdvertisingService(svcUUID)) {
      Serial.printf("✅ Servidor encontrado: %s\n", dev.getAddress().toString().c_str());

      pClient = NimBLEDevice::createClient();
      // Conectar usando dirección, no objeto
      if (!pClient->connect(dev.getAddress())) {
        Serial.println("❌ No se pudo conectar al servidor");
        NimBLEDevice::deleteClient(pClient);
        pClient = nullptr;
        return false;
      }
      Serial.println("✅ Conectado al servidor");

      NimBLERemoteService* srv = pClient->getService(svcUUID);
      if (!srv) { Serial.println("❌ Servicio no encontrado"); pClient->disconnect(); return false; }

      pChar = srv->getCharacteristic(NimBLEUUID(CHARACTERISTIC_UUID));
      if (!pChar || !pChar->canWrite()) {
        Serial.println("❌ Característica no válida");
        pClient->disconnect();
        return false;
      }

      return true;
    }
  }

  Serial.println("❌ Servidor BLE no detectado");
  return false;
}

void setup() {
  Serial.begin(115200);
  NimBLEDevice::init("");

  Serial.println("🔎 Iniciando escaneo y conexión...");
  if (!connectToServer()) {
    Serial.println("⚠️ Reintentando en 5s...");
    delay(5000);
    if (!connectToServer()) {
      Serial.println("⚠️ No se pudo conectar tras segundo intento");
    }
  }
}

void loop() {
  if (pClient && pClient->isConnected() && pChar) {
    float t = random(200, 300) / 10.0;
    float h = random(400, 700) / 10.0;
    String msg = CLIENT_ID + " - Temp:" + String(t,1) + "°C Hum:" + String(h,1) + "%";
    pChar->writeValue(msg.c_str());
    Serial.println("📤 " + msg);
  } else {
    Serial.println("⚠️ Desconectado. Reintentando conexión...");
    if (pClient) {
      pClient->disconnect();
      NimBLEDevice::deleteClient(pClient);
      pClient = nullptr;
    }
    delay(1000);
    setup();  // reintenta
    return;
  }
  delay(1000);
}

