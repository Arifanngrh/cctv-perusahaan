import cv2
import json
import requests
import time
import multiprocessing
import threading
import signal
import sys
from ultralytics import YOLO
from urllib.parse import quote

API_URL = "http://127.0.0.1:8000/counter"
STREAM_URL = "http://127.0.0.1:8000/frame"

def shutdown(sig, frame):
    print("🛑 STOP AI")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)

# =============================
# CAMERA READER (ANTI DELAY)
# =============================
class CameraReader:
    def __init__(self, rtsp):
        self.cap = cv2.VideoCapture(rtsp)
        self.frame = None
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while True:
            if not self.cap.isOpened():
                self.cap.open(self.cap)
                time.sleep(1)
                continue

            ret, frame = self.cap.read()
            if ret:
                self.frame = frame

    def get(self):
        return self.frame


# =============================
# MAIN
# =============================
def run_camera(camera):

    NAME = camera["name"]
    RTSP = camera["rtsp"]

    print("🚀 START:", NAME)

    model = YOLO("yolo11n.pt")
    helmet_model = YOLO("helmet.pt")

    try:
        model.to("cuda")
        helmet_model.to("cuda")
        print("⚡ GPU")
    except:
        print("🐢 CPU")

    model.fuse()

    reader = CameraReader(RTSP)
    session = requests.Session()

    IN, OUT = 0, 0
    helmet_count, no_helmet_count = 0, 0

    history = {}
    track_time = {}
    helmet_history = {}

    TIMEOUT = 4
    OFFSET = 8              # 🔥 lebih stabil crossing
    COOLDOWN = 0.5

    line_position = 0.5
    direction = "NORMAL"

    last_fetch = 0
    last_frame = 0
    last_api = 0

    while True:

        now = time.time()
        frame = reader.get()

        if frame is None:
            time.sleep(0.01)
            continue

        frame = cv2.resize(frame, (640, 360))
        h, w = frame.shape[:2]

        cam = quote(NAME)

        # =============================
        # FETCH CONFIG
        # =============================
        if now - last_fetch > 0.2:
            try:
                line_position = session.get(
                    f"http://127.0.0.1:8000/line/{cam}", timeout=1
                ).json().get("position", 0.5)

                direction = session.get(
                    f"http://127.0.0.1:8000/direction/{cam}", timeout=1
                ).json().get("mode", "NORMAL")

                direction = direction.upper()
                if direction not in ["NORMAL", "REVERSE"]:
                    direction = "NORMAL"

            except:
                pass

            last_fetch = now

        line_x = int(w * line_position)

        cv2.line(frame, (line_x, 0), (line_x, h), (0, 0, 255), 2)

        # =============================
        # TRACK
        # =============================
        try:
            results = model.track(
                frame,
                persist=True,
                conf=0.3,
                tracker="bytetrack.yaml",
                verbose=False
            )
        except:
            continue

        if results[0].boxes.id is not None:

            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()

            for box, tid, cls in zip(boxes, ids, classes):

                if int(cls) != 0:
                    continue

                tid = int(tid)
                x1, y1, x2, y2 = map(int, box)

                if (x2 - x1) < 40:
                    continue

                cx = (x1 + x2) // 2
                track_time[tid] = now

                # =============================
                # HELMET (1x per object)
                # =============================
                if tid not in helmet_history:
                    crop = frame[y1:y2, x1:x2]
                    helmet = False

                    try:
                        res = helmet_model(crop, conf=0.3)
                        for r in res:
                            for c in r.boxes.cls:
                                if int(c) == 0:
                                    helmet = True
                    except:
                        pass

                    if helmet:
                        helmet_count += 1
                    else:
                        no_helmet_count += 1

                    helmet_history[tid] = True

                # =============================
                # ZONE
                # =============================
                if cx < line_x - OFFSET:
                    zone = "LEFT"
                elif cx > line_x + OFFSET:
                    zone = "RIGHT"
                else:
                    zone = "MID"

                if tid not in history:
                    history[tid] = {"zone": zone}
                    continue

                prev = history[tid]["zone"]
                history[tid]["zone"] = zone

                # =============================
                # CROSSING (ANTI MISS)
                # =============================
                if prev == "LEFT" and zone == "RIGHT":

                    if direction == "NORMAL":
                        OUT += 1
                        print("➡️ OUT", OUT)
                    else:
                        IN += 1
                        print("⬅️ IN", IN)

                elif prev == "RIGHT" and zone == "LEFT":

                    if direction == "NORMAL":
                        IN += 1
                        print("⬅️ IN", IN)
                    else:
                        OUT += 1
                        print("➡️ OUT", OUT)

                cv2.rectangle(frame, (x1,y1),(x2,y2),(0,255,0),2)

        # =============================
        # CLEAN MEMORY
        # =============================
        expired = [tid for tid,t in track_time.items() if now-t > TIMEOUT]
        for tid in expired:
            history.pop(tid, None)
            track_time.pop(tid, None)
            helmet_history.pop(tid, None)

        # =============================
        # SEND API
        # =============================
        if now - last_api > 1:
            try:
                session.post(API_URL, json={
                    "camera": NAME,
                    "people_in": IN,
                    "people_out": OUT,
                    "helmet": helmet_count,
                    "no_helmet": no_helmet_count
                }, timeout=2)
            except:
                pass

            last_api = now

        # =============================
        # STREAM
        # =============================
        if now - last_frame > 0.05:
            try:
                _, jpg = cv2.imencode(".jpg", frame)
                session.post(
                    f"{STREAM_URL}/{cam}",
                    files={"file": ("f.jpg", jpg.tobytes())},
                    timeout=1
                )
            except:
                pass

            last_frame = now


# =============================
# MAIN
# =============================
if __name__ == "__main__":

    multiprocessing.set_start_method("spawn")

    with open("config.json") as f:
        config = json.load(f)

    for cam in config["cameras"]:
        multiprocessing.Process(target=run_camera, args=(cam,)).start()