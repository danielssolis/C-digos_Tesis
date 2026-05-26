#include <NimBLEDevice.h>

#define SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

String CLIENT_ID = "Cliente 1";
NimBLERemoteCharacteristic* pChar;
NimBLEClient* pClient;

void setup() {
  Serial.begin(115200);
  NimBLEDevice::init("");

  NimBLEScan* scan = NimBLEDevice::getScan();
  scan->setActiveScan(true);
  scan->start(5);
  
  NimBLEAdvertisedDevice* dev = nullptr;
  for (auto &d : scan->getResults().getDevices()) {
    if (d.isAdvertisingService(NimBLEUUID(SERVICE_UUID))) { dev = new NimBLEAdvertisedDevice(d); break; }
  }
  scan->clearResults();

  if (!dev) { Serial.println("❌ Servidor no encontrado"); return; }

  pClient = NimBLEDevice::createClient();
  if (!pClient->connect(dev)) { Serial.println("❌ Error al conectar"); return; }

  NimBLERemoteService* srv = pClient->getService(SERVICE_UUID);
  pChar = srv->getCharacteristic(CHARACTERISTIC_UUID);
}
void loop() {
  if (pClient && pClient->isConnected() && pChar) {
    String data = CLIENT_ID + " - " + String(random(200,300)/10.0,1) + "°C";
    pChar->writeValue(data.c_str());
    Serial.println("📤 " + data);
  }
  delay(1000);
}
