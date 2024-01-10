#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecureBearSSL.h>
#include <SoftwareSerial.h>


SoftwareSerial NodeMCU_SoftSerial (D1,D2); //RX, TX

const char *hotspotSSID = "AIDAMS_Setup_Network";
const char *hotspotPassword = "przM4IqXX7";
String serverUrl = "https://aidams.onrender.com";
ESP8266WebServer server(80);

unsigned long lastTime = 0;
unsigned long timerDelay = 3000;
bool is_registered = false;

char c;
String dataIn;

//device information
String DeviceProductKey = "aidamsnCRE33xuU8";
String DevicePassword = "przM4IqXX7";
String DeviceName = "";
String auth_key = "Rbasl70SeKdh1Roq";

//Arduino response:
bool is_opened = true;
bool is_auto_lock_activated = false;
bool is_opened_too_long = false;
bool is_tampered = false;
bool is_door_opened = false;
bool serverLockToggle = false;
bool serverAutoLockToggle = false;

//values
int prev_auto_lock_time = 15;
bool is_curfew_on = false;
String curfew_time = "";

void serialListener() {
  while(NodeMCU_SoftSerial.available()>0){
    c = NodeMCU_SoftSerial.read();
    Serial.print(c);
    if(c =='\n') {break;}
    else{ dataIn += c; }
  }
  if(c=='\n'){
    if(dataIn == "1 "){
      is_opened = false;
    }
    if(dataIn == "2 "){
      is_opened = true;
    }
    if(dataIn == "3 "){
      is_auto_lock_activated = false;
    }
    if(dataIn == "4 "){
      is_auto_lock_activated = true;
    }
    if(dataIn == "5 "){
      is_opened_too_long  = true;
    }
    if(dataIn == "6 "){
      is_tampered  = true;
    }
    if(dataIn == "9 "){
      is_door_opened  = false;
    }
    if(dataIn == "10 "){
      is_door_opened  = true;
    }
    c=0;
    dataIn="";
  }
  
}

void setup()
{
  Serial.begin(19200);

  // Set up NodeMCU as an Access Point (AP)
  WiFi.softAP(hotspotSSID, hotspotPassword);

  // Set up web server routes
  server.on("/", HTTP_GET, handleRoot);
  server.on("/connect", HTTP_POST, handleConnect);

  // Initialize D4 light as an output
  pinMode(D4, OUTPUT);

  //Open Serial Communication(Arduino-NodeMCU)
  NodeMCU_SoftSerial.begin(9600);

  server.begin();
}

String handleGETReq(String serverPath){
    std::unique_ptr<BearSSL::WiFiClientSecure>client(new BearSSL::WiFiClientSecure);

    // Ignore SSL certificate validation
    client->setInsecure();
    
    //create an HTTPClient instance
    HTTPClient https;
    
    Serial.println(serverPath);
    String payload = "";
    //Initializing an HTTPS communication using the secure client
    if (https.begin(*client, serverPath)) {  // HTTPS
      Serial.print("[HTTPS] GET...\n");
      // start connection and send HTTP header
      int httpCode = https.GET();
      // httpCode will be negative on error
      if (httpCode > 0) {
        // HTTP header has been send and Server response header has been handled
        Serial.printf("[HTTPS] GET... code: %d\n", httpCode);
        // file found at server
        if (httpCode == HTTP_CODE_OK || httpCode == HTTP_CODE_MOVED_PERMANENTLY) {
          payload = https.getString();
          is_registered = true;
          Serial.println(payload);
        }
      } else {
        Serial.printf("[HTTPS] GET... failed, error: %s\n", https.errorToString(httpCode).c_str());
        
      }
      
      https.end();
      return payload;
    } else {
      Serial.printf("[HTTPS] Unable to connect\n");
      return "";
    }
}

void loop()
{
  serialListener();
  if (WiFi.status() != WL_CONNECTED){
    server.handleClient();
  }
  else if ((millis() - lastTime) > timerDelay) {
    
    //Check WiFi connection status
    if(WiFi.status()== WL_CONNECTED){

      if (!is_registered){
        String serverPath = serverUrl+"/nodeMCU/device/register?dv_name="+DeviceName+"&dv_key="+DeviceProductKey+"&dv_password="+DevicePassword+"&auth_key="+auth_key;
        String inputString = handleGETReq(serverPath);
        char charArray[inputString.length() + 1];
        inputString.toCharArray(charArray, sizeof(charArray));

        // Split the string by ','
        char* token = strtok(charArray, ",");
        int index = 0;
        while (token != NULL) {

          if(index == 0 && atoi(token) != prev_auto_lock_time){
            prev_auto_lock_time = atoi(token);
            //auto locking time
            NodeMCU_SoftSerial.print(String(token)+" \n");
          }
          else if(index == 1 && strcmp(token, "False") == 0){
           //command arduino to toggle lock open or close
            NodeMCU_SoftSerial.print("7 \n");
          }
          else if (index == 2 && strcmp(token, "True") == 0){
            //command arduino to toggle auto locking
            NodeMCU_SoftSerial.print("8 \n");
          }
          index++;
          // Get the next token
          token = strtok(NULL, ",");
        }

      }
      else{
        String serverPath = serverUrl+"/nodeMCU/device/update?dv_key="+DeviceProductKey+"&is_opened="+is_opened+"&is_auto_lock_activated="+is_auto_lock_activated+"&is_door_opened="+is_door_opened+"&is_opened_too_long="+is_opened_too_long+"&is_tampered="+is_tampered+"&serverLockToggle="+serverLockToggle+"&serverAutoLockToggle="+serverAutoLockToggle+"&auth_key="+auth_key;
        is_opened_too_long = false;
        is_tampered = false;
        serverLockToggle = false;
        serverAutoLockToggle = false;
        String inputString = handleGETReq(serverPath);
        // Convert the String to a char array (c-string)
        char charArray[inputString.length() + 1];
        inputString.toCharArray(charArray, sizeof(charArray));

        // Split the string by ','
        char* token = strtok(charArray, ",");
        int index = 0;
        while (token != NULL) {

          if(index == 0 && atoi(token) != prev_auto_lock_time){
            prev_auto_lock_time = atoi(token);
            //auto locking time
            NodeMCU_SoftSerial.print(String(token)+" \n");
          }
          else if(index == 1){
            curfew_time = token;
            Serial.println("Curfew time changed: "+curfew_time);
          }
          else if (index == 2 && strcmp(token, "True") == 0){
            //command arduino to toggle lock open or close
            NodeMCU_SoftSerial.print("7 \n");
            serverLockToggle = true;
          }
          else if(index == 3 && strcmp(token, "True") == 0){
            //command arduino to toggle auto locking on or off
            NodeMCU_SoftSerial.print("8 \n");
            serverAutoLockToggle = true;
          }
          else if(index == 4 && strcmp(token, "True") == 0){

            Serial.println("Curfew is: "+is_curfew_on);
            is_curfew_on = !is_curfew_on;
          }
          else if(index == 5 && strcmp(token, "0") == 0){
           serverLockToggle = false;
          }
          else if(index == 6 && strcmp(token, "0") == 0){
            serverAutoLockToggle = false;
          }
          index++;
          // Get the next token
          token = strtok(NULL, ",");
        }
      }
    }
    else {
      Serial.println("WiFi Disconnected");
    }
    lastTime = millis();
  }
}

void handleRoot()
{
  String html = "<html><head><style>";
  html += "body { font-family: Arial, sans-serif; margin: 20px; background-color: #191F22; color:white;}";
  html += "form { max-width: 400px; margin: 0 auto; }";
  html += "h1 { text-align: center; padding-top:100px; padding-botton:100px; color:white;}";
  html += "h2 { margin-top: 20px; font-weight:400; color:white;}";
  html += "input { width: 100%; padding: 10px; margin-bottom: 15px; border-radius:10px; border:solid 1px black; background-color: #3B3B3B; color:white; }";
  html += "input[type='submit'] { background-color: #4CAF50; color: white; cursor: pointer; }";
  html += "</style></head><body>";
  html += "<h1>Welcome to Configuration Page</h1>";
  html += "<form action='/connect' method='post'>";
  html += "<h2>Device Credentials</h2>";
  html += "Device Product Key: <input type='text' name='device_product_key' required><br>";
  html += "Device Password: <input type='text' name='device_password' required><br>";
  html += "Device Name: <input type='text' name='device_name' required><br>";
  html += "<h2>Network Credentials</h2>";
  html += "SSID: <input type='text' name='ssid' required><br>";
  html += "Password: <input type='text' name='password' required><br>";
  html += "<input type='submit' style='background-color: #4CAF50;' value='Connect'></form>";
  html += "<script>";
  html += "function showAlert(message) { alert(message); }";
  html += "</script>";
  html += "</body></html>";

  server.send(200, "text/html", html);
}
void handleConnect()
{

  String userSSID = server.arg("ssid");
  String userPassword = server.arg("password");
  String deviceProductKey = server.arg("device_product_key");
  String devicePassword = server.arg("device_password");
  DeviceName = server.arg("device_name");
  
  // Perform validation and connect to home network
  // You may add additional validation if needed
  
  if (userSSID.length() > 0 && userPassword.length() > 0 && deviceProductKey == DeviceProductKey && devicePassword == DevicePassword && DeviceName.length() > 0)
  {
    connectToHomeNetwork(userSSID.c_str(), userPassword.c_str());
    server.send(200, "text/plain", "Connected to Home Network");
    digitalWrite(D4, LOW);
    // Display alert using JavaScript
    server.sendContent("<script>showAlert('Connected to Home Network');</script>");
  }
  else
  {
    server.send(403, "text/plain", "Invalid Credentials");

    // Display alert using JavaScript
    server.sendContent("<script>showAlert('Invalid Credentials');</script>");
  }
}

void connectToHomeNetwork(const char *ssid, const char *password)
{
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");

  unsigned long startTime = millis();

  while (WiFi.status() != WL_CONNECTED)
  {
    delay(1000);
    Serial.print(".");

    // Check if the timeout has elapsed (20 seconds)
    if (millis() - startTime > 20000)
    {
      Serial.println("\nConnection timeout. Returning to hotspot mode.");
      // Return to hotspot mode
      WiFi.softAP(hotspotSSID, hotspotPassword);
      
      return;
    }
  }
  Serial.println("\nConnected to WiFi");
  digitalWrite(D4, LOW);
}

