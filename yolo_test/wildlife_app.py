import asyncio

import cv2
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from ultralytics import YOLO

# --- LOGIC & AI ---
model = YOLO("yolo11n_openvino_model/")


async def detect_and_frame_gen(url):
    """
    Generator that captures frames, runs YOLO, and encodes to JPEG.
    """
    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            # AI Inference
            results = model(frame, stream=True, conf=0.25)
            for r in results:
                # Logic for "Async Triggering"
                if len(r.boxes) > 0:
                    # You can trigger an async task here without blocking the stream
                    # asyncio.create_task(my_alert_function())
                    pass
                frame = r.plot()

            # Encode to JPEG for the browser
            _, buffer = cv2.imencode(".jpg", frame)
            frame_bytes = buffer.tobytes()

            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )

            # Tiny sleep to allow other async tasks to run
            await asyncio.sleep(0.01)
    finally:
        cap.release()


# --- FASTAPI SETUP ---
app = FastAPI()


@app.get("/video_feed")
async def video_feed():
    url = "https://outbound-production.explore.org/stream-production-174/.m3u8"
    return StreamingResponse(
        detect_and_frame_gen(url),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/")
async def index():
    return {"message": "Go to /video_feed to see the stream"}
