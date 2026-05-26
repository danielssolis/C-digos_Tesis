#include <esp_now.h>
#include <WiFi.h>
#include "DHT.h"

#define DHTPIN 4       // Pin donde está conectado el DHT22
#define DHTTYPE DHT22  // Tipo de sensor

DHT dht(DHTPIN, DHTTYPE);

// Dirección MAC del receptor
uint8_t broadcastAddress[] = {0x40, 0x4C, 0xCA, 0x5E, 0xA0, 0xAC};


// Variables para almacenar lecturas del DHT22
float temperature;
float humidity;

// Variables para lecturas entrantes
float incomingTemp;
float incomingHum;

// Estado del envío
String success;

// Estructura de datos para enviar/recibir
typedef struct struct_message {
  float temp;
  float hum;
} struct_message;

struct_message DHTReadings;
struct_message incomingReadings;

esp_now_peer_info_t peerInfo;

// Callback cuando se envían datos
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  Serial.print("\r\nEstado del último paquete: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Envío exitoso" : "Fallo en el envío");
  success = (status == ESP_NOW_SEND_SUCCESS) ? "Envío exitoso :)" : "Fallo en el envío :(";
}

// Callback cuando se reciben datos
void OnDataRecv(const uint8_t *mac, const uint8_t *incomingData, int len) {
  memcpy(&incomingReadings, incomingData, sizeof(incomingReadings));
  Serial.print("Bytes recibidos: ");
  Serial.println(len);
  incomingTemp = incomingReadings.temp;
  incomingHum = incomingReadings.hum;
}

void setup() {
  Serial.begin(115200);
  dht.begin();

  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error al iniciar ESP-NOW");
    return;
  }

  esp_now_register_send_cb(OnDataSent);
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Error al agregar peer");
    return;
  }

  esp_now_register_recv_cb(esp_now_recv_cb_t(OnDataRecv));

   // Semilla para generar números aleatorios distintos cada vez
  randomSeed(analogRead(0));
}

void loop() {
  getReadings();

  DHTReadings.temp = temperature;
  DHTReadings.hum = humidity;

  esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *)&DHTReadings, sizeof(DHTReadings));

  if (result == ESP_OK) {
    Serial.println("Enviado con éxito");
  } else {
    Serial.println("Error enviando los datos");
  }

  updateDisplay();
  delay(5000);
}

void getReadings() {
  temperature = random(200, 300) / 10.0; // 20.0 - 30.0 °C
  humidity = random(400, 700) / 10.0;    // 40.0 - 70.0 %
}


void updateDisplay() {
  Serial.println("\n📤 DATOS GENERADOS (LOCALES)");
  Serial.print("Temperatura generada: ");
  Serial.print(temperature);
  Serial.println(" ºC");
  Serial.print("Humedad generada: ");
  Serial.print(humidity);
  Serial.println(" %");
  Serial.println("---------------------------");
  Serial.println("LECTURAS ENTRANTES");
  Serial.print("Temperatura: ");
  Serial.print(incomingReadings.temp);
  Serial.println(" ºC");
  Serial.print("Humedad: ");
  Serial.print(incomingReadings.hum);
  Serial.println(" %");
  Serial.println(success);
  Serial.println("---------------------------");
}