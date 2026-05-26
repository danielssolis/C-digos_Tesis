// NODO 1: ESP32 con Sensor PIR (Compatible ESP32 v3.x)
#include <esp_now.h>
#include <WiFi.h>
#include <esp_sleep.h>

// MAC Address de la ESP32 Principal (CÁMBIALA)
uint8_t receiverMAC[] = {0x40,0x22,0xD8,0x4F,0x56,0xEC};

// Pin del sensor PIR
#define PIR_PIN 13

// Estructura de datos a enviar
typedef struct {
  int nodeId;
  char sensorType[20];
  float value;
  unsigned long timestamp;
} SensorData;

SensorData myData;

// Callback compatible con ESP32 v3.x
void OnDataSent(const esp_now_send_info_t *info, esp_now_send_status_t status) {
  Serial.print("Estado de envío: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Éxito" : "Fallo");
}

void setup() {
  Serial.begin(115200);
  pinMode(PIR_PIN, INPUT);
  
  // Configurar WiFi en modo estación
  WiFi.mode(WIFI_STA);
  
  // Inicializar ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error inicializando ESP-NOW");
    return;
  }
  
  // Registrar callback
  esp_now_register_send_cb(OnDataSent);
  
  // Registrar peer
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, receiverMAC, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Error agregando peer");
    return;
  }
  
  Serial.println("Nodo PIR iniciado correctamente");
}

void loop() {
  // Leer sensor PIR
  int pirState = digitalRead(PIR_PIN);
  
  // Preparar datos
  myData.nodeId = 1;
  strcpy(myData.sensorType, "PIR");
  myData.value = pirState;
  myData.timestamp = millis();
  
  Serial.print("Leyendo PIR: ");
  Serial.println(pirState);
  
  // Enviar datos
  esp_err_t result = esp_now_send(receiverMAC, (uint8_t *) &myData, sizeof(myData));
  
  if (result == ESP_OK) {
    Serial.println("Datos enviados correctamente");
  } else {
    Serial.println("Error enviando datos");
  }
  
  // Entrar en deep sleep por 60 segundos
  Serial.println("Entrando en deep sleep por 60 segundos...");
  Serial.flush(); // Esperar a que termine de imprimir
  esp_sleep_enable_timer_wakeup(60 * 1000000ULL); // 60 segundos
  esp_deep_sleep_start();
}