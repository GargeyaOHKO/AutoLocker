import cv2
import mediapipe as mp
import serial
import time

# Define map_value function
def map_value(value, in_min, in_max, out_min, out_max):
    """ Map a value from one range to another. """
    return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

# Initialize serial communication with Arduino
arduino = serial.Serial('COM3', 9600)
time.sleep(2)

# Initialize MediaPipe face detection model
mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# Open the webcam
cap = cv2.VideoCapture(0)

# Flag to prevent multiple push servo triggers in quick succession
push_triggered = False
trigger_sent = False
last_trigger_time = time.time()
DEBOUNCE_INTERVAL = 2 
arduino.write("START_MOTOR\n".encode()) 
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Convert frame to RGB for MediaPipe processing
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detection.process(frame_rgb)
    face_detected = False
    if results.detections:
        for detection in results.detections:
            face_detected = True
            bbox = detection.location_data.relative_bounding_box
            h, w, _ = frame.shape
            x, y, w_box, h_box = int(bbox.xmin * w), int(bbox.ymin * h), int(bbox.width * w), int(bbox.height * h)

            # Draw bounding box around the detected face
            cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), (255, 0, 0), 2)

            # Calculate the center of the face
            face_center_x = x + w_box // 2
            face_center_y = y + h_box // 2

            # Map face coordinates to pan and tilt servo angles
            pan_angle = map_value(face_center_x, 0, frame.shape[1], 160, 20)
            tilt_angle = map_value(face_center_y, 0, frame.shape[0], 20, 160)

            # Send servo angles to Arduino
            arduino.write(f"P{pan_angle}\n".encode())
            arduino.write(f"T{tilt_angle}\n".encode())

            # Trigger motor and push servo if a face is detected and not already triggered
        if face_detected and (not trigger_sent or time.time() - last_trigger_time > DEBOUNCE_INTERVAL):
            arduino.write("TRIGGER_PUSH\n".encode())
            trigger_sent = True
            last_trigger_time = time.time()

    else:
        # If no face is detected, stop the motor
        push_triggered = False  # Reset push trigger flag
    # Show the frame with face detection
    cv2.imshow('Face Detection', frame)
    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Reset servos to initial position and stop the motors
arduino.write("P90\n".encode())  # Reset pan servo to 90 degrees
arduino.write("T90\n".encode())  # Reset tilt servo to 90 degrees
arduino.write("STOP_MOTOR\n".encode())
arduino.write("STOP_DETECT_MOTOR\n".encode())
cap.release()
cv2.destroyAllWindows()
arduino.close()
