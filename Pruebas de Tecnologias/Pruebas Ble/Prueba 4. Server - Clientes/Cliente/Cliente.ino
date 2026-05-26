#include <NimBLEDevice.h>

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

String CLIENT_ID = "Cliente 2";  // Cambia a Cliente 2 y Cliente 3 en cada ESP32

NimBLEClient* pClient = nullptr;
NimBLERemoteCharacteristic* pChar = nullptr;

bool connectToServer() {
  NimBLEScan* scan = NimBLEDevice::getScan();
  scan->setActiveScan(true);                 // Configura escaneo activo
  Serial.println("🔎 Escaneando servidor...");
  NimBLEScanResults res = scan->start(5, false);
  Serial.printf("🔍 Dispositivos encontrados: %d\n", res.getCount());
  scan->clearResults();

  NimBLEUUID svcUUID(SERVICE_UUID);
  for (int i = 0; i < res.getCount(); i++) {
    NimBLEAdvertisedDevice dev = res.getDevice(i);
    if (!dev.isAdvertisingService(svcUUID)) continue;

    Serial.printf("✅ Servidor detectado: %s\n", dev.getAddress().toString().c_str());

    // Crea cliente y conecta usando dirección MAC
    if (pClient) {
      pClient->disconnect();
      NimBLEDevice::deleteClient(pClient);
    }
    pClient = NimBLEDevice::createClient();
    if (!pClient->connect(dev.getAddress())) {
      Serial.println("❌ No se pudo conectar al servidor");
      return false;
    }
    Serial.println("✅ Conectado al servidor");

    // Obtén la característica
    NimBLERemoteService* srv = pClient->getService(svcUUID);
    if (!srv) { Serial.println("❌ Servicio no encontrado"); return false; }
    pChar = srv->getCharacteristic(NimBLEUUID(CHARACTERISTIC_UUID));
    if (!pChar || !pChar->canWrite()) {
      Serial.println("❌ Característica no writable");
      return false;
    }
    return true;
  }

  Serial.println("❌ Servidor BLE no detectado");
  return false;
}

void setup() {
  Serial.begin(115200);
  NimBLEDevice::init("");  // inicializa sin nombre para cliente

  // Intenta conectar; reintenta en 5s si falla
  if (!connectToServer()) {
    Serial.println("⚠️ Reintentando en 5s...");
    delay(5000);
    connectToServer();
  }
}

void loop() {
  if (pClient && pClient->isConnected() && pChar) {
    float t = random(200, 300) / 10.0;
    float h = random(400, 700) / 10.0;
    String msg = CLIENT_ID + " - Temp:" + String(t, 1) + "°C Hum:" + String(h, 1) + "%";
    pChar->writeValue(msg.c_str());
    Serial.println("📤 " + msg);
  } else {
    Serial.println("⚠️ Desconectado; reconectando...");
    delay(1000);
    setup();  // reintenta conexión
    return;
  }
  delay(1000);
}

