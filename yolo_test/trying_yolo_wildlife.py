# This is a test! The window is hard to close

from contextlib import contextmanager

import cv2
from ultralytics import YOLO


@contextmanager
def camera_stream(source=0):
    """
    Context manager to safely open and release a camera or URL stream.
    """
    cap = cv2.VideoCapture(source)
    # Optimization: Reduces the internal buffer size to prevent "lag" in live streams
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {source}")
    try:
        yield cap
    finally:
        print(f"\nCleanup: Releasing resource from {source}...")
        cap.release()
        cv2.destroyAllWindows()
        cv2.waitKey(1)


def run_cam(model_path, source=0):
    model = YOLO(model_path)

    with camera_stream(source) as cap:
        print("Looking for bears. Press 'q' in the window to exit.")

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("Stream lost.")
                break

            results = model(frame, stream=True, conf=0.25)

            # Draw results on the frame
            for r in results:
                annotated_frame = r.plot()

            # Resize to 720p height for display while maintaining aspect ratio
            h, w = annotated_frame.shape[:2]
            scale = 720 / h
            display_frame = cv2.resize(annotated_frame, (int(w * scale), 720))

            cv2.imshow("National Park Monitor", display_frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


if __name__ == "__main__":
    model_dir = "yolo11n_openvino_model/"
    url = "https://outbound-production.explore.org/stream-production-174/.m3u8"

    run_cam(model_dir, source=url)
