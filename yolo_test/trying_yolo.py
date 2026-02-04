import time
from contextlib import contextmanager

import chime
import cv2
from ultralytics import YOLO


class SurveillanceSystem:
    def __init__(self, model_path, cooldown=5, confidence=0.5):
        # Default arguments instead of hardcoded constants
        self.model = YOLO(model_path, task="detect")
        self.cooldown = cooldown
        self.min_conf = confidence
        self.last_alert_time = 0
        chime.theme("zelda")

    def should_alert(self, current_time):
        """Check if enough time has passed since the last alert."""
        return (current_time - self.last_alert_time) > self.cooldown

    def trigger_alert(self, frame, current_time):
        """Handle the sound and saving the file."""
        print("🚨 Intruder Alert!")
        chime.success()
        self.last_alert_time = current_time

        # Save snapshot
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        cv2.imwrite(f"intruder_{timestamp}.jpg", frame)

    def process_frame(self, frame):
        """Detect persons and return the annotated frame."""
        results = self.model.predict(
            frame, classes=[0], conf=self.min_conf, verbose=False
        )

        person_detected = False
        annotated_frame = frame.copy()

        for r in results:
            annotated_frame = r.plot()
            if len(r.boxes) > 0:
                person_detected = True

        return person_detected, annotated_frame


@contextmanager
def camera_stream(device_index=0):
    """
    Context manager to safely open and release the webcam.
    """
    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video device {device_index}")
    try:
        yield cap
    finally:
        print("\nCleanup: Releasing camera resource...")
        cap.release()
        cv2.destroyAllWindows()
        cv2.waitKey(1)


def run_cam(model_path):
    system = SurveillanceSystem(model_path)

    with camera_stream(0) as cap:
        print("Surveillance Active. Press 'q' to exit.")

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            now = time.time()
            detected, annotated_frame = system.process_frame(frame)

            if detected and system.should_alert(now):
                system.trigger_alert(annotated_frame, now)

            cv2.imshow("Surveillance Feed", annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


if __name__ == "__main__":
    run_cam("yolo11n_openvino_model/")
