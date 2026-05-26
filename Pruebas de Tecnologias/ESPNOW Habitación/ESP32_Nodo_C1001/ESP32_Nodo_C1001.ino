/* Nodo DFRobot #2 – ESP32
   Envía datos por ESP-NOW al maestro y entra en Deep Sleep
*/

#include <esp_now.h>
#include <WiFi.h>
#include "DFRobot_HumanDetection.h"

DFRobot_HumanDetection hu(&Serial1);

// MAC del maestro
uint8_t masterMac[6] = {0x40,0x22,0xD8,0x4F,0x56,0xEC};

typedef struct {
  uint8_t msgType; // 3 = DFRobot2
  char mac[18];
  uint8_t in_bed_2;
  uint8_t sleep_state_2;
  int respiration_2;
  int heartbeat_2;
} NodePacket;

NodePacket pkt;

// -------- FUNCIÓN DE FALLO SEGURO --------
void failRestart(const char* msg) {
  Serial.println(msg);
  delay(1500);
  ESP.restart();
}

// -----------------------------------------------------------
// NUEVA FIRMA OBLIGATORIA EN ESP-IDF 5.x
// -----------------------------------------------------------
void onDataSent(const wifi_tx_info_t *tx_info, esp_now_send_status_t status) {
  Serial.print("Estado envío: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "OK" : "FALLÓ");
}

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200, SERIAL_8N1, 16, 17);
  delay(300);

  Serial.println("Inicializando sensor DFRobot...");

  while (hu.begin() != 0) {
    Serial.println("Error iniciando DFRobot2");
    delay(1000);
  }

  hu.configWorkMode(hu.eSleepMode);
  hu.configLEDLight(hu.eHPLed, 1);
  hu.sensorRet();

  delay(800);

  pkt.msgType = 3;

  // ---- WiFi obligatorio ----
  WiFi.mode(WIFI_STA);

  // MAC del nodo
  String myMac = WiFi.macAddress();
  myMac.toCharArray(pkt.mac, 18);

  // ---- Iniciar ESP-NOW ----
  if (esp_now_init() != ESP_OK) {
    failRestart("Error iniciando ESP-NOW");
  }

  // Registrar callback nuevo
  esp_now_register_send_cb(onDataSent);

  // ---- Agregar peer maestro ----
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, masterMac, 6);
  peer.channel = 0;
  peer.encrypt = false;

  if (esp_now_add_peer(&peer) != ESP_OK) {
    failRestart("Error agregando peer (maestro)");
  }

  // -------- LEER DATOS DFRobot2 --------
  uint8_t inBed       = hu.smSleepData(hu.eInOrNotInBed);
  uint8_t sleepSt     = hu.smSleepData(hu.eSleepState);

  sSleepComposite comp = hu.getSleepComposite();

  pkt.in_bed_2      = inBed;
  pkt.sleep_state_2 = sleepSt;
  pkt.respiration_2 = comp.averageRespiration;
  pkt.heartbeat_2   = comp.averageHeartbeat;

  Serial.printf("DFRobot2 -> inBed=%d | sleep=%d | HR=%d | RR=%d\n",
                pkt.in_bed_2,
                pkt.sleep_state_2,
                pkt.heartbeat_2,
                pkt.respiration_2);

  // -------- ENVIAR --------
  esp_err_t res = esp_now_send(masterMac, (uint8_t*)&pkt, sizeof(pkt));
  if (res == ESP_OK) {
    Serial.println("Paquete enviado correctamente.");
  } else {
    Serial.printf("Error esp_now_send: %d\n", res);
  }

  delay(250);

  // -------- DEEP SLEEP --------
  const uint64_t SLEEP_TIME_S = 60;

  Serial.printf("Entrando en deep sleep por %llu segundos...\n", SLEEP_TIME_S);
  esp_sleep_enable_timer_wakeup(SLEEP_TIME_S * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {}
