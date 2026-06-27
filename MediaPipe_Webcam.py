import cv2
import mediapipe as mp
import serial
import time

# Define map_value function
def map_value(value, in_min, in_max, out_min, out_max):
    """ Map a value from one range to another, ensuring it stays within bounds. """
    value = max(in_min, min(value, in_max))  # Ensure value is within input range
    return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

# Initialize serial communication with Arduino
arduino = serial.Serial('COM3', 9600)
time.sleep(2)

# Initialize MediaPipe face detection
mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.7)

# Open the webcam
cap = cv2.VideoCapture(0)

# Get the webcam resolution dynamically
ret, frame = cap.read()
if not ret:
    print("Error: Could not read frame from webcam.")
    cap.release()
    exit()

frame_height, frame_width, _ = frame.shape
print(f"Webcam Resolution: {frame_width}x{frame_height}")

# Set servo ranges (Swapped Min & Max to fix inversion)
PAN_MIN, PAN_MAX = 160, 20  # Swapped to fix left-right inversion
TILT_MIN, TILT_MAX = 20, 160  # Swapped to fix up-down inversion

# Servo reset positions
PAN_CENTER = (PAN_MAX + PAN_MIN) // 2
TILT_CENTER = (TILT_MAX + TILT_MIN) // 2

# Debounce trigger
trigger_sent = False
last_trigger_time = time.time()
DEBOUNCE_INTERVAL = 2

arduino.write("START_MOTOR\n".encode())

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detection.process(frame_rgb)
    face_detected = False

    if results.detections:
        for detection in results.detections:
            face_detected = True
            bbox = detection.location_data.relative_bounding_box
            x, y, w_box, h_box = (int(bbox.xmin * frame_width), int(bbox.ymin * frame_height),
                                  int(bbox.width * frame_width), int(bbox.height * frame_height))

            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), (255, 0, 0), 2)

            # Face center
            face_center_x = x + w_box // 2
            face_center_y = y + h_box // 2

            # **Fixed Pan & Tilt Mapping by Swapping Min & Max**
            pan_angle = map_value(face_center_x, 0, frame_width, PAN_MIN, PAN_MAX)  
            tilt_angle = map_value(face_center_y, 0, frame_height, TILT_MIN, TILT_MAX)  

            # Send angles to Arduino
            arduino.write(f"P{pan_angle}\n".encode())
            arduino.write(f"T{tilt_angle}\n".encode())

            # Trigger push mechanism
        if face_detected and (not trigger_sent or time.time() - last_trigger_time > DEBOUNCE_INTERVAL):
            arduino.write("TRIGGER_PUSH\n".encode())
            trigger_sent = True
            last_trigger_time = time.time()

    # Show the frame
    cv2.imshow('Face Detection', frame)

    # Exit on 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Reset servos and stop motors
arduino.write(f"P{PAN_CENTER}\n".encode())
arduino.write(f"T{TILT_CENTER}\n".encode())
arduino.write("STOP_MOTOR\n".encode())
arduino.write("STOP_DETECT_MOTOR\n".encode())

cap.release()
cv2.destroyAllWindows()
arduino.close()
