#include <NimBLEDevice.h>

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

String CLIENT_ID = "Cliente 1";  // Cambiar en cada ESP: Cliente 1, Cliente 2, Cliente 3

NimBLEClient* pClient = nullptr;
NimBLERemoteCharacteristic* pChar = nullptr;

void setup() {
  Serial.begin(115200);
  NimBLEDevice::init("");               // Siempre inicializa con cadena vacía

  // Escaneo
  NimBLEScan* scan = NimBLEDevice::getScan();
  scan->setActiveScan(true);
  Serial.println("🔎 Escaneando servidor...");
  NimBLEScanResults results = scan->start(5, false);
  Serial.printf("🔍 Encontrados %d dispositivos\n", results.getCount());

  NimBLEUUID svcUUID(SERVICE_UUID);

  // Buscar y clonar el dispositivo
  for (int i = 0; i < results.getCount(); i++) {
    NimBLEAdvertisedDevice tmp = results.getDevice(i);
    if (!tmp.isAdvertisingService(svcUUID)) continue;

    Serial.printf("✅ Servidor detectado: %s\n", tmp.getAddress().toString().c_str());

    // Clonar el objeto para crear un puntero válido
    NimBLEAdvertisedDevice* advDevice = new NimBLEAdvertisedDevice(tmp);

    // Conexión
    pClient = NimBLEDevice::createClient();
    Serial.println("🔌 Intentando conectar...");
    if (pClient->connect(advDevice)) {
      Serial.println("✅ Conectado al servidor");

      // Obtener servicio y característica
      NimBLERemoteService* srv = pClient->getService(svcUUID);
      if (srv) {
        pChar = srv->getCharacteristic(CHARACTERISTIC_UUID);
        if (pChar && pChar->canWrite()) {
          Serial.println("✔️ Característica lista para escritura");
        }
      }
    } else {
      Serial.println("❌ Error al conectar al servidor");
      delete advDevice;
      pClient = nullptr;
    }
    break;
  }

  scan->clearResults();
}

void loop() {
  if (pClient && pClient->isConnected() && pChar && pChar->canWrite()) {
    float t = random(200, 300) / 10.0;
    float h = random(400, 700) / 10.0;
    String msg = CLIENT_ID + " - Temp:" + String(t, 1) + "°C Hum:" + String(h, 1) + "%";
    pChar->writeValue(msg.c_str());
    Serial.println("📤 " + msg);
  } else {
    Serial.println("⚠️ Cliente desconectado, reintentando escaneo...");
    delay(500);
    setup();  // reintentar conexión
    return;
  }
  delay(1000);
}

