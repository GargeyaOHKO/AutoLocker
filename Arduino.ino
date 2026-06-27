#include <Servo.h>
const int panServoPin = 11;
const int tiltServoPin = 10;
const int motorPin = 9;
const int detectMotorPin = 6; // New motor pin for face detection

Servo panServo;
Servo tiltServo;

void setup() {
  panServo.attach(panServoPin);
  tiltServo.attach(tiltServoPin);

  pinMode(motorPin, OUTPUT);
  pinMode(detectMotorPin, OUTPUT);

  digitalWrite(motorPin, HIGH);       // Motor OFF initially
  digitalWrite(detectMotorPin, HIGH); // Detection motor OFF initially

  panServo.write(90); // Center position
  tiltServo.write(90);

  Serial.begin(9600);
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    Serial.println(command); // Debugging: Print received command

    if (command.startsWith("P")) { // Pan position command
      int panPos = command.substring(1).toInt();
      panPos = constrain(panPos, 30, 150);
      panServo.write(panPos);
    } 
    else if (command.startsWith("T")) { // Tilt position command
      int tiltPos = command.substring(1).toInt();
      tiltPos = constrain(tiltPos, 30, 150);
      tiltServo.write(tiltPos);
    } 
    else if (command == "START_DETECT_MOTOR") { // Start detection motor
      digitalWrite(detectMotorPin, LOW); // Motor ON
    } 
    else if (command == "STOP_DETECT_MOTOR") { // Stop detection motor
      digitalWrite(detectMotorPin, HIGH); // Motor OFF
    } 
    else if (command == "START_MOTOR") {
      digitalWrite(motorPin, LOW);  // Main motor ON
    } 
    else if (command == "STOP_MOTOR") {
      digitalWrite(motorPin, HIGH); // Main motor OFF
    }
  }
}
