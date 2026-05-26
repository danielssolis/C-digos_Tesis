/* Nodo SCT-013 (ESP32) - Deep Sleep + ESP-NOW
   IMPORTANTE:
   - Debes usar una resistencia burden (33–62Ω).
   - La señal del SCT013 debe estar centrada en VCC/2 usando divisor resistivo.
*/

#include <esp_now.h>
#include <WiFi.h>

#define ANALOG_PIN 34
#define SAMPLE_COUNT 500
#define ADC_REF 3.3
#define ADC_MAX 4095.0
#define V_OFFSET 1.65
#define SCT_CAL 30.0    

// MAC del maestro
uint8_t masterMac[6] = {0x40, 0x22, 0xD8, 0x4F, 0x56, 0xEC};

typedef struct {
  uint8_t msgType;    
  char mac[18];
  float corriente;
} NodePacket;

NodePacket pkt;

// -------- Manejo de fallo seguro --------
void failRestart(const char* msg) {
  Serial.println(msg);
  delay(1500);
  ESP.restart();
}

/*
 * NUEVO CALLBACK PARA ESP-IDF 5.x
 * Recibe wifi_tx_info_t en vez de uint8_t* (como antes)
 */
void onDataSent(const wifi_tx_info_t *tx_info, esp_now_send_status_t status) {
  Serial.print("Estado envío: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "ÉXITO" : "FALLÓ");
}

void setup() {
  Serial.begin(115200);
  delay(300);

  WiFi.mode(WIFI_STA);

  String macStr = WiFi.macAddress();
  macStr.toCharArray(pkt.mac, 18);
  pkt.msgType = 2;

  // ------- Iniciar ESP-NOW -------
  if (esp_now_init() != ESP_OK) {
    failRestart("Error iniciando ESP-NOW");
  }

  /*
   * REGISTRAR EL NUEVO CALLBACK (IDF 5.x)
   */
  esp_now_register_send_cb(onDataSent);

  // ------- Registrar maestro -------
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, masterMac, 6);
  peer.channel = 0;
  peer.encrypt = false;

  if (esp_now_add_peer(&peer) != ESP_OK) {
    failRestart("Error agregando peer maestro");
  }

  Serial.println("Iniciando medición SCT013...");

  // ------- Medición -------
  double sumSquares = 0.0;

  for (int i = 0; i < SAMPLE_COUNT; i++) {
    int raw = analogRead(ANALOG_PIN);

    float v = (raw / ADC_MAX) * ADC_REF;
    float centered = v - V_OFFSET;

    sumSquares += centered * centered;

    delayMicroseconds(500);
  }

  float meanSq = sumSquares / SAMPLE_COUNT;
  float Vrms = sqrt(meanSq);
  float Iamps = Vrms * SCT_CAL;

  pkt.corriente = Iamps;

  Serial.printf("Vrms = %.4f V | Corriente = %.3f A\n", Vrms, Iamps);

  // ------- Enviar ESP-NOW -------
  esp_err_t res = esp_now_send(masterMac, (uint8_t*)&pkt, sizeof(pkt));

  if (res == ESP_OK) {
    Serial.println("Paquete SCT enviado correctamente.");
  } else {
    Serial.printf("Error al enviar ESP-NOW: %d\n", res);
  }

  delay(200);

  // ------- Entrar a Deep Sleep -------
  const uint64_t SLEEP_TIME_S = 60;

  Serial.printf("Entrando en Deep Sleep (%llu s)...\n", SLEEP_TIME_S);

  esp_sleep_enable_timer_wakeup(SLEEP_TIME_S * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {}


