/*
 ============================================================
  AQI PREDICTION SYSTEM — ESP32 IoT Sensor Code
  Hardware: ESP32 + MQ-7 + MQ-135 + SDS011 dust sensor
 ============================================================
  WIRING:
    SDS011 TX  → ESP32 GPIO16 (RX2)
    SDS011 RX  → ESP32 GPIO17 (TX2)
    MQ-7  AOUT → ESP32 GPIO34 (ADC)
    MQ-135AOUT → ESP32 GPIO35 (ADC)
    All sensors VCC → 5V, GND → GND

  LIBRARIES TO INSTALL in Arduino IDE:
    - ArduinoJson (by Benoit Blanchon)
    - HTTPClient (built-in with ESP32)

  HOW TO UPLOAD:
    1. Install Arduino IDE
    2. Add ESP32 board: File > Preferences > Board URL:
       https://dl.espressif.com/dl/package_esp32_index.json
    3. Tools > Board > ESP32 Dev Module
    4. Install ArduinoJson library
    5. Fill YOUR_WIFI_NAME, YOUR_WIFI_PASSWORD, SERVER_IP
    6. Upload!
 ============================================================
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ── CONFIG — CHANGE THESE ──────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Your PC's IP address (run "ipconfig" to find it)
// Example: "192.168.1.5"
const char* SERVER_IP     = "192.168.1.5";
const int   SERVER_PORT   = 8000;

// Station API key from your Django admin → Stations page
const char* API_KEY       = "your-station-api-key-here";

// How often to send data (milliseconds)
const int SEND_INTERVAL = 60000;  // 60 seconds

// ── PIN DEFINITIONS ────────────────────────────────
#define MQ7_PIN    34   // CO sensor (MQ-7) analog pin
#define MQ135_PIN  35   // Air quality sensor analog pin
// SDS011 uses Serial2 (GPIO16=RX, GPIO17=TX)

// ── GLOBALS ────────────────────────────────────────
unsigned long lastSend = 0;

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, 16, 17);  // SDS011

  Serial.println("\n=== AQI IoT Sensor Starting ===");

  // Connect to WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

// ── READ SDS011 DUST SENSOR ─────────────────────────
float pm25 = 0, pm10 = 0;
bool readSDS011() {
  byte buf[10];
  if (Serial2.available() >= 10) {
    if (Serial2.read() == 0xAA) {
      buf[0] = 0xAA;
      for (int i=1; i<10; i++) buf[i] = Serial2.read();
      if (buf[9] == 0xAB) {
        pm25 = ((buf[3] * 256) + buf[2]) / 10.0;
        pm10 = ((buf[5] * 256) + buf[4]) / 10.0;
        return true;
      }
    }
  }
  // Fallback: simulated values if sensor not connected
  pm25 = 35.0 + random(-10, 20);
  pm10 = 65.0 + random(-15, 30);
  return false;
}

// ── READ GAS SENSORS ────────────────────────────────
float readCO() {
  int raw = analogRead(MQ7_PIN);
  // Convert ADC reading to mg/m³ (simplified calibration)
  float voltage = raw * (3.3 / 4095.0);
  float co = voltage * 3.5;  // Adjust calibration factor
  return max(0.1f, co);
}

float readAirQuality() {
  int raw = analogRead(MQ135_PIN);
  return raw;  // Raw value for NO2/SO2 estimation
}

// ── SEND DATA TO DJANGO SERVER ───────────────────────
void sendToServer(float pm25, float pm10, float co, float so2, float no2, float o3) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi disconnected!");
    return;
  }

  String url = "http://" + String(SERVER_IP) + ":" + SERVER_PORT + "/api/iot/";

  HTTPClient http;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  // Build JSON body
  StaticJsonDocument<256> doc;
  doc["api_key"] = API_KEY;
  doc["pm25"]    = pm25;
  doc["pm10"]    = pm10;
  doc["co"]      = co;
  doc["so2"]     = so2;
  doc["no2"]     = no2;
  doc["o3"]      = o3;

  String body;
  serializeJson(doc, body);

  Serial.println("📤 Sending: " + body);
  int code = http.POST(body);

  if (code == 200) {
    String response = http.getString();
    Serial.println("✅ Response: " + response);

    // Parse response
    StaticJsonDocument<256> resp;
    deserializeJson(resp, response);
    String category = resp["category"];
    int aqi = resp["aqi"];
    Serial.println("🌬️  AQI: " + String(aqi) + " | Category: " + category);
  } else {
    Serial.println("❌ HTTP Error: " + String(code));
  }

  http.end();
}

void loop() {
  unsigned long now = millis();

  if (now - lastSend >= SEND_INTERVAL) {
    lastSend = now;

    Serial.println("\n--- Reading Sensors ---");

    // Read all sensors
    readSDS011();
    float co  = readCO();
    int   raw = readAirQuality();

    // Simplified NO2/SO2/O3 from MQ-135 (in real project use dedicated sensors)
    float no2 = (raw / 4095.0) * 80.0;
    float so2 = (raw / 4095.0) * 50.0;
    float o3  = (raw / 4095.0) * 60.0;

    Serial.printf("PM2.5: %.1f | PM10: %.1f | CO: %.2f\n", pm25, pm10, co);
    Serial.printf("NO2: %.1f | SO2: %.1f | O3: %.1f\n", no2, so2, o3);

    // Send to server
    sendToServer(pm25, pm10, co, so2, no2, o3);
  }

  delay(100);
}
