// ESP32 PRINCIPAL - Receptor ESP-NOW + HTTP POST (Compatible v3.x)
#include <esp_now.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "DFRobot_HumanDetection.h"

// Credenciales WiFi
const char* ssid = "Pdegrado24";
const char* password = "20Pgrado26$";

// URL del servidor PHP (Cambia la IP por la de tu PC)
const char* serverURL = "http://192.168.0.73/sensor_data.php";

// Crear objeto del sensor local (usando Serial1 en pines 16 RX, 17 TX)
DFRobot_HumanDetection huLocal(&Serial1);

// Estructura de datos recibidos
typedef struct {
  int nodeId;
  char sensorType[20];
  float value;
  unsigned long timestamp;
} SensorData;

SensorData incomingData;

// Callback cuando se reciben datos (Compatible ESP32 v3.x)
void OnDataRecv(const esp_now_recv_info_t *info, const uint8_t *incomingDataBuf, int len) {
  memcpy(&incomingData, incomingDataBuf, sizeof(incomingData));
  
  Serial.println("\n=== Datos recibidos ===");
  Serial.print("Nodo ID: ");
  Serial.println(incomingData.nodeId);
  Serial.print("Sensor: ");
  Serial.println(incomingData.sensorType);
  Serial.print("Valor: ");
  Serial.println(incomingData.value);
  Serial.println("=======================\n");
  
  // Enviar a MySQL
  sendToDatabase(incomingData.nodeId, incomingData.sensorType, 
                 incomingData.value, incomingData.timestamp);
}

void sendToDatabase(int nodeId, const char* sensorType, float value, unsigned long timestamp) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("✗ WiFi desconectado - Reintentando...");
    WiFi.reconnect();
    delay(2000);
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("✗ No se pudo reconectar a WiFi");
      return;
    }
  }
  
  HTTPClient http;
  
  // Configurar timeout más largo
  http.setTimeout(10000); // 10 segundos
  
  Serial.println("--- Intentando enviar a servidor ---");
  Serial.print("URL: ");
  Serial.println(serverURL);
  
  // Intentar conectar al servidor
  if (!http.begin(serverURL)) {
    Serial.println("✗ Error: No se pudo iniciar conexión HTTP");
    Serial.println("Verifica que la URL sea correcta y el servidor esté activo");
    http.end();
    return;
  }
  
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  
  String postData = "node_id=" + String(nodeId) + 
                    "&sensor_type=" + String(sensorType) +
                    "&value=" + String(value, 2) +
                    "&timestamp=" + String(timestamp);
  
  Serial.print("Datos a enviar: ");
  Serial.println(postData);
  
  int httpResponseCode = http.POST(postData);
  
  if (httpResponseCode > 0) {
    Serial.print("✓ Código HTTP: ");
    Serial.println(httpResponseCode);
    String response = http.getString();
    Serial.print("✓ Respuesta: ");
    Serial.println(response);
  } else {
    Serial.print("✗ Error en POST: ");
    Serial.println(httpResponseCode);
    
    // Mostrar detalles del error
    switch(httpResponseCode) {
      case -1:
        Serial.println("  → Error de conexión: El servidor no responde");
        break;
      case -11:
        Serial.println("  → Timeout: El servidor no respondió a tiempo");
        break;
      default:
        Serial.println("  → Error desconocido");
    }
  }
  
  http.end();
  Serial.println("------------------------------------");
}

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200, SERIAL_8N1, 16, 17); // RX=16, TX=17
  
  Serial.println("\n=== Iniciando ESP32 Principal ===");
  
  // Inicializar sensor C1001 local
  Serial.println("Inicializando sensor C1001 local...");
  while (huLocal.begin() != 0) {
    Serial.println("Error inicializando sensor local, reintentando...");
    delay(1000);
  }
  Serial.println("✓ Sensor C1001 local inicializado");
  
  // Configurar en modo Sleep Detection
  Serial.println("Configurando modo Sleep Detection...");
  while (huLocal.configWorkMode(huLocal.eSleepMode) != 0) {
    Serial.println("Error configurando modo, reintentando...");
    delay(1000);
  }
  Serial.println("✓ Modo Sleep Detection configurado");
  
  // Configurar LED y reset
  huLocal.configLEDLight(huLocal.eHPLed, 1);
  huLocal.sensorRet();
  delay(500);
  
  Serial.print("Modo de trabajo actual: ");
  switch (huLocal.getWorkMode()) {
    case 1: Serial.println("Detección de caídas"); break;
    case 2: Serial.println("Detección de sueño"); break;
    default: Serial.println("Error lectura");
  }
  
  // Conectar a WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("Conectando a WiFi");
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ Conectado a WiFi");
    Serial.print("Dirección IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n✗ No se pudo conectar a WiFi");
  }
  
  // Obtener y mostrar MAC Address (IMPORTANTE: Anótala para los nodos)
  Serial.println("\n========================================");
  Serial.print("MAC Address de esta ESP32: ");
  Serial.println(WiFi.macAddress());
  Serial.println("COPIA ESTA MAC PARA LOS NODOS SENSORES");
  Serial.println("========================================\n");
  
  // Inicializar ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("✗ Error inicializando ESP-NOW");
    return;
  }
  
  Serial.println("✓ ESP-NOW iniciado");
  
  // Registrar callback de recepción
  esp_now_register_recv_cb(OnDataRecv);
  
  Serial.println("✓ Sistema listo - Esperando datos de nodos...\n");
  
  // DIAGNÓSTICO DE CONEXIÓN
  Serial.println("\n╔════════════════════════════════════════╗");
  Serial.println("║   DIAGNÓSTICO DE CONEXIÓN AL SERVIDOR  ║");
  Serial.println("╚════════════════════════════════════════╝");
  Serial.print("URL configurada: ");
  Serial.println(serverURL);
  Serial.print("IP de esta ESP32: ");
  Serial.println(WiFi.localIP());
  Serial.println("\nPara verificar el servidor:");
  Serial.println("1. Abre un navegador en tu PC");
  Serial.print("2. Ve a: ");
  Serial.println(serverURL);
  Serial.println("3. Deberías ver un mensaje de error JSON");
  Serial.println("   (eso significa que el PHP funciona)");
  Serial.println("\nSi no funciona, verifica:");
  Serial.println("→ XAMPP Apache está corriendo (botón verde)");
  Serial.println("→ El archivo sensor_data.php está en C:/xampp/htdocs/");
  Serial.println("→ La IP es la correcta (cmd → ipconfig)");
  Serial.println("→ Firewall no está bloqueando el puerto 80");
  Serial.println("════════════════════════════════════════\n");
}

void loop() {
  // Leer sensor local cada 60 segundos
  static unsigned long lastRead = 0;
  if (millis() - lastRead > 60000) {
    
    Serial.println("\n=== Leyendo sensor C1001 local ===");
    
    // Leer presencia en cama
    int inBed = huLocal.smSleepData(huLocal.eInOrNotInBed);
    Serial.print("En cama: ");
    Serial.println(inBed == 1 ? "SÍ" : "NO");
    sendToDatabase(0, "MMWAVE_LOCAL_BED", inBed, millis());
    delay(100);
    
    // Leer estado de sueño
    int sleepState = huLocal.smSleepData(huLocal.eSleepState);
    Serial.print("Estado sueño: ");
    switch(sleepState) {
      case 0: Serial.println("Sueño profundo"); break;
      case 1: Serial.println("Sueño ligero"); break;
      case 2: Serial.println("Despierto"); break;
      case 3: Serial.println("Ninguno"); break;
      default: Serial.println("Error lectura");
    }
    sendToDatabase(0, "MMWAVE_LOCAL_SLEEP", sleepState, millis());
    delay(100);
    
    // Obtener datos compuestos de sueño
    sSleepComposite composite = huLocal.getSleepComposite();
    if (composite.presence == 1) {
      Serial.println("Datos adicionales del sueño:");
      Serial.printf("  Respiración promedio: %d\n", composite.averageRespiration);
      Serial.printf("  Ritmo cardíaco promedio: %d\n", composite.averageHeartbeat);
      
      // Enviar datos de respiración y ritmo cardíaco
      sendToDatabase(0, "RESPIRATION", composite.averageRespiration, millis());
      delay(100);
      sendToDatabase(0, "HEARTBEAT", composite.averageHeartbeat, millis());
    }
    
    Serial.println("===================================\n");
    lastRead = millis();
  }
  
  delay(100);
}