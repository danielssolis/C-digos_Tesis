#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEClient.h>
#include <BLEAddress.h>

static BLEUUID serviceUUID("12345678-1234-1234-1234-1234567890ab");
static BLEUUID characteristicUUID("87654321-4321-4321-4321-abcdefabcdef");

BLEAddress serverAddress("XX:XX:XX:XX:XX:XX"); // ← reemplaza con la dirección MAC del servidor BLE
BLERemoteCharacteristic* pRemoteCharacteristic;
BLEClient* pClient;

void setup() {
  Serial.begin(115200);
  BLEDevice::init("ESP32-C6-Client");

  pClient = BLEDevice::createClient();

  if (pClient->connect(serverAddress)) {
    Serial.println("Conectado al servidor");
    BLERemoteService* pRemoteService = pClient->getService(serviceUUID);
    if (pRemoteService) {
      pRemoteCharacteristic = pRemoteService->getCharacteristic(characteristicUUID);
    }
  } else {
    Serial.println("No se pudo conectar al servidor");
  }
}

void loop() {
  if (pClient->isConnected() && pRemoteCharacteristic != nullptr) {
    int temp = random(20, 30); // Simula temperatura
    String data = String(temp);
    pRemoteCharacteristic->writeValue(data.c_str(), data.length());
    Serial.print("Dato enviado: ");
    Serial.println(data);
  } else {
    Serial.println("No conectado. Intentando reconectar...");
  }
  delay(1000);
}

