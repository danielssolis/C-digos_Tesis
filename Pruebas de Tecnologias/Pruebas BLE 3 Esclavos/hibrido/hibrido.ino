#include <NimBLEDevice.h>

/*  ← MAC Bluetooth reales de tus 3 esclavos  */
const char* slaveMacs[] = {
  "40:22:D8:4F:80:72",
  "24:6F:28:BB:BB:BB",
  "24:6F:28:CC:CC:CC"
};
const int numSlaves = sizeof(slaveMacs) / sizeof(slaveMacs[0]);

#define SERVICE_UUID        "12345678-1234-1234-1234-1234567890ab"
#define CHARACTERISTIC_UUID "abcdefab-1234-1234-1234-abcdefabcdef"

/* --- Callback de notificación --- */
void notifyCB(NimBLERemoteCharacteristic* /*ch*/,
              uint8_t* data, size_t len, bool /*isNotify*/) {
  Serial.print("Dato recibido: ");
  for (size_t i = 0; i < len; ++i) Serial.write(data[i]);
  Serial.println();
}

/* --- Conexión + suscripción a un esclavo --- */
void connectToSlave(const char* macAddress) {
  NimBLEAddress addr(std::string(macAddress), BLE_ADDR_PUBLIC);   // ✔️ Constructor correcto
  NimBLEClient* client = NimBLEDevice::createClient();

  Serial.printf("Conectando a %s …\n", macAddress);
  if (!client->connect(addr)) {
    Serial.println("❌  No se pudo conectar");
    NimBLEDevice::deleteClient(client);
    return;
  }

  NimBLERemoteService* svc = client->getService(SERVICE_UUID);
  if (!svc) { Serial.println("Servicio no encontrado"); client->disconnect(); return; }

  NimBLERemoteCharacteristic* ch = svc->getCharacteristic(CHARACTERISTIC_UUID);
  if (!ch) { Serial.println("Característica no encontrada"); client->disconnect(); return; }

  if (!ch->canNotify()) { Serial.println("La característica no permite notify"); client->disconnect(); return; }

  if (!ch->subscribe(true, notifyCB)) {
    Serial.println("Error al suscribirse"); client->disconnect(); return;
  }

  Serial.println("✅  Suscripción exitosa, esperando datos…");
}

void setup() {
  Serial.begin(115200);
  NimBLEDevice::init("");

  for (int i = 0; i < numSlaves; ++i) {
    connectToSlave(slaveMacs[i]);
    delay(250);                           // pequeño respiro entre conexiones
  }
}

void loop() {
  /*  Nada que hacer: las notificaciones se imprimen en notifyCB()  */
  delay(1000);
}
