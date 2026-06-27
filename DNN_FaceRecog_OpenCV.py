import cv2
import numpy as np
import serial
import time

# Initialize serial communication with Arduinozzpppppppppppppppppaz-55555555555555555
arduino = serial.Serial('COM3', 9600)  # Update with your Arduino's COM port
time.sleep(2)

# Load the DNN model for face detectionz
net = cv2.dnn.readNetFromCaffe(
    "C:/Users/parab/OneDrive/Documents/Arduino/KJ Turret V3/deploy (1).prototxt",  # Path to prototxt file
    "C:/Users/parab/OneDrive/Documents/Arduino/KJ Turret V3/res10_300x300_ssd_iter_140000 (1).caffemodel"  # Path to caffemodel file
)

# Enable OpenCV CUDA backend if available
if cv2.cuda.getCudaEnabledDeviceCount() > 0:
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)

# Open the webcam
cap = cv2.VideoCapture(0)

def map_value(value, in_min, in_max, out_min, out_max):
    """ Map a value from one range to another. """
    return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

motor_running = False
prev_pan_angle = 90  # Initial pan angle
prev_tilt_angle = 90  # Initial tilt angle

arduino.write("START_MOTOR\n".encode()) 
try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Prepare the image for DNN
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))

        # Perform detection
        net.setInput(blob)
        detections = net.forward()

        face_detected = False
        best_confidence = 0
        best_box = None

        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.7:  # Confidence threshold
                # Find the best detection
                if confidence > best_confidence:
                    best_confidence = confidence
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    best_box = box.astype("int")

        if best_box is not None:
            face_detected = True
            (x, y, x1, y1) = best_box
            cv2.rectangle(frame, (x, y), (x1, y1), (255, 0, 0), 2)

            # Calculate center of the face
            face_center_x = (x + x1) // 2
            face_center_y = (y + y1) // 2

            # Map values for servos
            pan_angle = map_value(face_center_x, 0, w, 160, 20)
            tilt_angle = map_value(face_center_y, 0, h, 20, 160)

            # Smooth the servo movements
            pan_angle = int(0.7 * prev_pan_angle + 0.3 * pan_angle)
            tilt_angle = int(0.7 * prev_tilt_angle + 0.3 * tilt_angle)
            prev_pan_angle, prev_tilt_angle = pan_angle, tilt_angle

            arduino.write(f"P{pan_angle}\n".encode())
            arduino.write(f"T{tilt_angle}\n".encode())

        # Control the detection motor based on face detection
        if face_detected:
            if not motor_running:
                arduino.write("START_DETECT_MOTOR\n".encode())
                motor_running = True
        else:
            if motor_running:
                arduino.write("STOP_DETECT_MOTOR\n".encode())
                motor_running = False

        cv2.imshow('Face Detection', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    # Reset servos to initial position and stop the motors
    arduino.write("P90\n".encode())  # Reset pan servo to 90 degrees
    arduino.write("T90\n".encode())  # Reset tilt servo to 90 degrees
    arduino.write("STOP_MOTOR\n".encode())
    arduino.write("STOP_DETECT_MOTOR\n".encode())
    cap.release()
    cv2.destroyAllWindows()
    arduino.close()
