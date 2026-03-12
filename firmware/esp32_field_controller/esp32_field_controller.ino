/*
  Ingenious Irrigation - ESP32 Field Controller
  Target: SparkFun ESP32 Thing Plus

  This sketch turns the ESP32 into a field-side controller that receives
  line-based commands from the Raspberry Pi over USB serial and responds with
  one-line JSON payloads.

  Commands:
    PING
    STATUS
    SENSORS
    ALL_OFF
    ZONE 1 ON
    ZONE 1 OFF

  Notes:
  - This version is intentionally simple and durable.
  - It currently supports one relay (Zone 1) because your current hardware is a
    single-channel relay module.
  - You can expand this to multiple zones later by adding more relay pins and
    extending the command handler.
*/

#include <Arduino.h>
#include <DHT.h>

#ifndef DHTTYPE
#define DHTTYPE DHT11
#endif

static const uint8_t DHT_PIN = 4;
static const uint8_t RELAY_PIN = 26;
static const bool RELAY_ACTIVE_LOW = true;
static const uint8_t MAX_LINE = 120;

DHT dht(DHT_PIN, DHTTYPE);
String lineBuffer;
bool zone1On = false;
unsigned long bootMs = 0;

void writeRelay(bool on) {
  zone1On = on;
  bool level = RELAY_ACTIVE_LOW ? !on : on;
  digitalWrite(RELAY_PIN, level ? HIGH : LOW);
}

void printBool(bool value) {
  Serial.print(value ? "true" : "false");
}

void printOkPrefix() {
  Serial.print("{\"ok\":true,");
}

void printError(const String &msg) {
  Serial.print("{\"ok\":false,\"error\":\"");
  for (size_t i = 0; i < msg.length(); ++i) {
    char c = msg[i];
    if (c == '"' || c == '\\') {
      Serial.print('\\');
    }
    if (c >= 32 && c <= 126) {
      Serial.print(c);
    }
  }
  Serial.println("\"}");
}

void cmdPing() {
  printOkPrefix();
  Serial.print("\"reply\":\"pong\",\"uptime_ms\":");
  Serial.print(millis());
  Serial.println("}");
}

void cmdStatus() {
  printOkPrefix();
  Serial.print("\"relay_on\":");
  printBool(zone1On);
  Serial.print(",\"zones\":{\"1\":");
  printBool(zone1On);
  Serial.print("},\"uptime_ms\":");
  Serial.print(millis());
  Serial.println("}");
}

void cmdSensors() {
  float humidity = dht.readHumidity();
  float tempC = dht.readTemperature();
  bool sensorOk = !(isnan(humidity) || isnan(tempC));

  printOkPrefix();
  Serial.print("\"driver\":\"esp32_dht11\",\"sensor_ok\":");
  printBool(sensorOk);
  Serial.print(",\"relay_on\":");
  printBool(zone1On);
  Serial.print(",\"zones\":{\"1\":");
  printBool(zone1On);
  Serial.print("}");

  if (sensorOk) {
    float tempF = tempC * 9.0f / 5.0f + 32.0f;
    Serial.print(",\"humidity\":");
    Serial.print(humidity, 1);
    Serial.print(",\"temperature_c\":");
    Serial.print(tempC, 1);
    Serial.print(",\"temperature_f\":");
    Serial.print(tempF, 1);
  } else {
    Serial.print(",\"humidity\":null,\"temperature_c\":null,\"temperature_f\":null");
  }

  // Future-ready placeholders. Populate these once you add the hardware.
  Serial.print(",\"soil_moisture_pct\":null,\"pressure_psi\":null");
  Serial.println("}");
}

void cmdAllOff() {
  writeRelay(false);
  printOkPrefix();
  Serial.println("\"relay_on\":false,\"zones\":{\"1\":false}}");
}

void cmdZone(const String &rest) {
  int firstSpace = rest.indexOf(' ');
  if (firstSpace < 0) {
    printError("ZONE syntax invalid");
    return;
  }

  String zonePart = rest.substring(0, firstSpace);
  String statePart = rest.substring(firstSpace + 1);
  zonePart.trim();
  statePart.trim();
  statePart.toUpperCase();

  int zone = zonePart.toInt();
  if (zone != 1) {
    printError("Only zone 1 is configured in this firmware");
    return;
  }

  if (statePart == "ON") {
    writeRelay(true);
  } else if (statePart == "OFF") {
    writeRelay(false);
  } else {
    printError("ZONE state must be ON or OFF");
    return;
  }

  printOkPrefix();
  Serial.print("\"zone\":1,\"relay_on\":");
  printBool(zone1On);
  Serial.print(",\"zones\":{\"1\":");
  printBool(zone1On);
  Serial.println("}}");
}

void handleCommand(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) {
    return;
  }

  String upper = cmd;
  upper.toUpperCase();

  if (upper == "PING") {
    cmdPing();
    return;
  }
  if (upper == "STATUS") {
    cmdStatus();
    return;
  }
  if (upper == "SENSORS") {
    cmdSensors();
    return;
  }
  if (upper == "ALL_OFF") {
    cmdAllOff();
    return;
  }
  if (upper.startsWith("ZONE ")) {
    cmdZone(cmd.substring(5));
    return;
  }

  printError("Unknown command");
}

void setup() {
  bootMs = millis();
  Serial.begin(115200);
  delay(250);

  pinMode(RELAY_PIN, OUTPUT);
  writeRelay(false);

  dht.begin();
  lineBuffer.reserve(MAX_LINE);

  // Emit a single boot banner the Pi can ignore if it opens the serial port late.
  Serial.println("{\"ok\":true,\"boot\":true,\"device\":\"ingenious_esp32_field_controller\"}");
}

void loop() {
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      String cmd = lineBuffer;
      lineBuffer = "";
      handleCommand(cmd);
      return;
    }
    if (lineBuffer.length() < MAX_LINE) {
      lineBuffer += c;
    }
  }
}
