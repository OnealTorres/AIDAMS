#include <Servo.h>
#include <SoftwareSerial.h>

SoftwareSerial Arduino_SoftSerial(10,11);// RX TX

// C++ code

//Time seconds
int auto_lock_time = 15;
int door_is_open_warning = 20;
unsigned long doorOpenedTime = 0;
const unsigned long timeThreshold = 30;
unsigned long autolockstartTime = 0;

//PINS
int piezoPin = 7;
int servoPin = 4;
int echoPin = 6;
int trigPin = 5;
int duration=0;
int distance=0;

//LEDS 0: red 1: green
int led[3]={2,3,8};

//status
bool is_start = true;
bool is_opened = true;
bool is_door_opened = true;
bool auto_locking = false;
bool is_break_in = false;
bool is_door_opened_message_shown = false;
bool is_break_in_message_shown = false;
bool autolocktimestart = false;

//servo
Servo lockServo;


//serial toggler
int toggleOpenClose = 0;
int toggleAutoLocking = 0;
int listen_to_string = 0;
char c;
String dataIn;

void setup()
{
  lockServo.attach(servoPin);
  pinMode(piezoPin, OUTPUT);
  pinMode(led[0], OUTPUT);
  pinMode(led[1], OUTPUT);
  pinMode(led[2], OUTPUT);
  pinMode(trigPin,	OUTPUT);
  pinMode(echoPin,	INPUT);
  Serial.begin(19200);
  Arduino_SoftSerial.begin(9600);
  
}

bool isNumeric(const char* str) {
  for (int i = 0; str[i] != '\0'; i++) {
    // Check if the character is not a digit
    if (!isdigit(str[i])) {
      return false;
    }
  }
  return true;
}

bool prev_door_status = is_door_opened;
void calculate_distance(){
  //sets the tigger pin active for 10 microseconds
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  //reads the echo pin and returns the sound wave travel time
  duration = pulseIn(echoPin, HIGH);
  //calculates the distance
  distance = duration * 0.034 / 2;
  
  //door monitor
  if(distance > 10){
  	is_door_opened = true;
    if(is_door_opened != prev_door_status){
      prev_door_status = is_door_opened;
      Arduino_SoftSerial.print("10 \n");
    }
  }
  else if(distance > 0){
    is_door_opened = false; 
    if(is_door_opened != prev_door_status){
      prev_door_status = is_door_opened;
      Arduino_SoftSerial.print("9 \n");
    }
  } 
}

void serialListener() {
    if (Serial.available() > 0) {
    // Read the incoming string
    char incomingBuffer[50]; // Adjust the size based on your requirements
    memset(incomingBuffer, 0, sizeof(incomingBuffer)); // Clear the buffer

    int bytesRead = Serial.readBytesUntil('\n', incomingBuffer, sizeof(incomingBuffer) - 1);

    // Check the command
    if (bytesRead > 0) {
      // Null-terminate the string
      incomingBuffer[bytesRead] = '\0';

      // Compare with C-style strings
      if (strcmp(incomingBuffer, "1") == 0 && isNumeric(incomingBuffer)) {
        toggleOpenClose = 1;
      } else if (strcmp(incomingBuffer, "2") == 0 && isNumeric(incomingBuffer)) {
        toggleAutoLocking = 1;
      } else if (isNumeric(incomingBuffer)) {
        auto_lock_time = atoi(incomingBuffer);
      }
    }
  }

  while(Arduino_SoftSerial.available()>0){
    c = Arduino_SoftSerial.read();
    Serial.print(c);
    if(c =='\n') {break;}
    else{ dataIn += c; }
  }
  if(c=='\n'){
    if(dataIn == "7 "){
      toggleOpenClose = 1;
    }
    else if(dataIn == "8 "){
      toggleAutoLocking = 1;
    }
    else if (dataIn.length() > 0) {
      auto_lock_time = dataIn.toInt();
    }
    c=0;
    dataIn="";
  }
}

void loop()
{
  //clears the trigger pin condition
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  
  //calulates the distance to check if open or closed
  calculate_distance();

  //listens to serial monitor inputs
  serialListener();
  
  //startup setup
  if(is_start){
    delay(10);
    lockServo.write(0);
    delay(10);
  	digitalWrite(led[1], HIGH);
  	is_start = false;
    Serial.println("Lock Status: Opened");
    if(auto_locking){
      Serial.println("Auto Locking: Enabled");
    }else Serial.println("Auto Locking: Disabled");
    Serial.println("---------------------------");
  }
  
  //toggle auto locking
  if(toggleAutoLocking == 1){
    auto_locking = !auto_locking;
    toggleAutoLocking = 0;
    delay(100);
    if(auto_locking){
      digitalWrite(led[2], HIGH);
      Serial.println("Auto Locking: Enabled");
      autolockstartTime = millis();
      autolocktimestart = false;
      Arduino_SoftSerial.print("4 \n");
    }else{
      digitalWrite(led[2], LOW);
      Serial.println("Auto Locking: Disabled");
      Arduino_SoftSerial.print("3 \n");
    } 
    Serial.println("---------------------------");
  }
  
  //break in detection
  if(!is_opened && is_door_opened && !is_break_in_message_shown){
    is_break_in = true;
    is_break_in_message_shown = true;
    Serial.println("Break In Warning! Please Call 911");
    Serial.println("----------------------------------");
    Arduino_SoftSerial.print("6 \n");
  }
  
  //buzzer
  if(is_break_in and !is_opened){
    tone(piezoPin, 1000, 100);
    delay(500);
  }
  //detects button events
  if( toggleOpenClose == 1){
    calculate_distance();
    //close
    if(is_opened && !is_door_opened){
      	digitalWrite(led[1], LOW);
      	delay(100);
    	  digitalWrite(led[0], HIGH);
      	delay(5);
      	lockServo.write(180);
      	is_opened = false;
      	Serial.println("Lock Status: Closed");
      	if(auto_locking){
      		Serial.println("Auto Locking: Enabled");
      	}else Serial.println("Auto Locking: Disabled");
      	Serial.println("---------------------------");
      	delay(5);
        autolocktimestart = false;
        is_break_in = false;
        is_break_in_message_shown = false;
        toggleOpenClose = 0;
        Arduino_SoftSerial.print("1 \n");
	  }
    //open
    else if(!is_opened && !is_door_opened){
        
        digitalWrite(led[0], LOW);
        delay(300);
        digitalWrite(led[1], HIGH);
        delay(5);
        lockServo.write(0);
        is_opened = true;
        is_break_in = false;
        Serial.println("Lock Status: Opened");
        if(auto_locking){
          Serial.println("Auto Locking: Enabled");
        }else Serial.println("Auto Locking: Disabled");
        Serial.println("---------------------------");
        delay(5);
        toggleOpenClose = 0;
        delay(100);
        Arduino_SoftSerial.print("2 \n");
        autolockstartTime = millis();
    }
    else{
        Serial.println("Please close the door!");
        Serial.println("---------------------------");
        toggleOpenClose = 0;
        delay(5);
    }
  }

  //door opened for too long detection
  if (is_opened && is_door_opened && is_door_opened_message_shown == false) {
    if (doorOpenedTime == 0) { 
      doorOpenedTime = millis(); // Record the time when the door is opened
    }

    // Check if 30 seconds have passed since the door was opened
    if (millis() - doorOpenedTime >= timeThreshold * 1000) {
      Serial.println("Warning: Door is opened for too long!");
      Serial.println("---------------------------");
      is_door_opened_message_shown = true;
      Arduino_SoftSerial.print("5 \n");
    }
  } else if(!is_opened && !is_door_opened) {
    doorOpenedTime = 0;
    is_door_opened_message_shown = false;
  }
  
  if(is_opened && !is_door_opened && !autolocktimestart){
    autolockstartTime = millis();
    autolocktimestart = true;
  }
  
  //door auto locking 
  if(auto_locking ){
    //checks if the lock is opened and door is closed
    calculate_distance();
    delay(200);

    if(is_opened && is_door_opened){
      autolockstartTime = millis();
    }
    
    if(millis() - autolockstartTime > auto_lock_time *1000 && !is_door_opened && is_opened){
      
      if(!is_door_opened){
        //automatically closes the lock after 5 sec 
        digitalWrite(led[1], LOW);
        delay(300);
        digitalWrite(led[0], HIGH);
        delay(5);
        lockServo.write(180);
        is_opened = false;
        Serial.println("Lock Status: Closed");
        autolocktimestart = false;
        autolockstartTime = millis();
        if(auto_locking){
          Serial.println("Auto Locking: Enabled");
        }else Serial.println("Auto Locking: Disabled");
        Serial.println("---------------------------");
        Arduino_SoftSerial.print("9 \n");
        Arduino_SoftSerial.print("1 \n");
        is_break_in = false;
        is_break_in_message_shown = false;
      }
    }
  }
}