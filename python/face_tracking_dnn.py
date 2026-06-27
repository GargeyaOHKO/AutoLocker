"""
AutoLocker - Vision Guided Robotic Perception Platform
Author: Gargeya Parab

Description
-----------
Performs real-time face detection using OpenCV's DNN face detector and
controls a pan-tilt mechanism through an Arduino Uno over USB serial.
"""

from pathlib import Path
import time
import cv2
import numpy as np
import serial

# =========================
# Configuration
# =========================
SERIAL_PORT = "COM3"
BAUD_RATE = 9600

CONFIDENCE_THRESHOLD = 0.70

PAN_MIN = 160
PAN_MAX = 20
TILT_MIN = 20
TILT_MAX = 160

INITIAL_PAN = 90
INITIAL_TILT = 90

CAMERA_INDEX = 0

MODEL_DIR = Path("models")
PROTOTXT = MODEL_DIR / "deploy.prototxt"
MODEL = MODEL_DIR / "res10_300x300_ssd_iter_140000.caffemodel"


def map_value(value, in_min, in_max, out_min, out_max):
    """Maps a value from one range to another."""
    return int((value - in_min) * (out_max - out_min) /
               (in_max - in_min) + out_min)


def initialize_dnn():
    net = cv2.dnn.readNetFromCaffe(str(PROTOTXT), str(MODEL))

    if cv2.cuda.getCudaEnabledDeviceCount() > 0:
        print("[INFO] CUDA detected. Using GPU.")
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
    else:
        print("[INFO] CUDA not available. Using CPU.")

    return net


def main():

    print("[INFO] Connecting to Arduino...")
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE)
    time.sleep(2)

    print("[INFO] Loading face detection model...")
    net = initialize_dnn()

    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    previous_pan = INITIAL_PAN
    previous_tilt = INITIAL_TILT

    motor_running = False

    fps_start = time.time()
    frame_counter = 0
    fps = 0

    arduino.write(b"START_MOTOR\n")

    try:
        while True:

            ret, frame = cap.read()

            if not ret:
                break

            frame_counter += 1

            h, w = frame.shape[:2]

            blob = cv2.dnn.blobFromImage(
                cv2.resize(frame, (300, 300)),
                1.0,
                (300, 300),
                (104.0, 177.0, 123.0)
            )

            net.setInput(blob)
            detections = net.forward()

            best_box = None
            best_confidence = 0
            face_detected = False

            for i in range(detections.shape[2]):

                confidence = detections[0, 0, i, 2]

                if confidence > CONFIDENCE_THRESHOLD and confidence > best_confidence:
                    best_confidence = confidence

                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    best_box = box.astype(int)

            if best_box is not None:

                face_detected = True

                x1, y1, x2, y2 = best_box

                cv2.rectangle(frame, (x1, y1), (x2, y2),
                              (255, 0, 0), 2)

                face_center_x = (x1 + x2) // 2
                face_center_y = (y1 + y2) // 2

                pan_angle = map_value(
                    face_center_x,
                    0,
                    w,
                    PAN_MIN,
                    PAN_MAX
                )

                tilt_angle = map_value(
                    face_center_y,
                    0,
                    h,
                    TILT_MIN,
                    TILT_MAX
                )

                pan_angle = int(previous_pan * 0.7 + pan_angle * 0.3)
                tilt_angle = int(previous_tilt * 0.7 + tilt_angle * 0.3)

                previous_pan = pan_angle
                previous_tilt = tilt_angle

                arduino.write(f"P{pan_angle}\n".encode())
                arduino.write(f"T{tilt_angle}\n".encode())

            if face_detected:

                if not motor_running:
                    arduino.write(b"START_DETECT_MOTOR\n")
                    motor_running = True

            else:

                if motor_running:
                    arduino.write(b"STOP_DETECT_MOTOR\n")
                    motor_running = False

            elapsed = time.time() - fps_start

            if elapsed >= 1:
                fps = frame_counter / elapsed
                fps_start = time.time()
                frame_counter = 0

            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            cv2.imshow("AutoLocker - Face Tracking", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:

        print("[INFO] Resetting system...")

        arduino.write(f"P{INITIAL_PAN}\n".encode())
        arduino.write(f"T{INITIAL_TILT}\n".encode())

        arduino.write(b"STOP_MOTOR\n")
        arduino.write(b"STOP_DETECT_MOTOR\n")

        cap.release()
        cv2.destroyAllWindows()
        arduino.close()

        print("[INFO] Shutdown complete.")


if __name__ == "__main__":
    main()
