/*  ===== ESCLAVO BLE con NimBLE ===== */
#include <NimBLEDevice.h>         // Instala “NimBLE-Arduino” por tu Gestor de Bibliotecas

#define SERVICE_UUID        "12345678-1234-1234-1234-1234567890ab"
#define CHAR_UUID           "abcd1234-1234-1234-1234-abcdef123456"

NimBLECharacteristic *pChar;

void setup() {
  Serial.begin(115200);
  NimBLEDevice::init("Esclavo1");          // “Esclavo2”, “Esclavo3”… en los otros módulos

  NimBLEServer *pServer  = NimBLEDevice::createServer();
  NimBLEService *pSvc    = pServer->createService(SERVICE_UUID);

  pChar = pSvc->createCharacteristic(
            CHAR_UUID,
            NIMBLE_PROPERTY::READ   |
            NIMBLE_PROPERTY::NOTIFY );

  pSvc->start();
  NimBLEAdvertising *adv = NimBLEDevice::getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->start();

  Serial.println("Esclavo listo → anunciando…");
}

void loop() {
  int dato = random(20, 30);                        // Simula sensor
  pChar->setValue(String(dato).c_str());
  pChar->notify();                                  // 🔔 Enviar notificación
  Serial.print("Enviado: "); Serial.println(dato);
  delay(1000);
}
