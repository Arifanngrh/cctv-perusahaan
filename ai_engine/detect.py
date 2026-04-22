import cv2
import json
import requests
import time
import multiprocessing
import threading
import signal
import sys
import os
from ultralytics import YOLO
from urllib.parse import quote

# =============================
# GLOBAL PROCESS LIST (FIX CTRL+C)
# =============================
processes = []

# =============================
# FIX IMPORT DATABASE
# =============================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

from database import update_daily_counter, save_detection

STREAM_URL = "http://127.0.0.1:8000/frame"


# =============================
# SHUTDOWN HANDLER (FIX TOTAL STOP)
# =============================
def shutdown(sig, frame):
    print("\n🛑 STOP ALL CAMERA PROCESS")

    for p in processes:
        if p.is_alive():
            p.terminate()

    for p in processes:
        p.join()

    os._exit(0)


signal.signal(signal.SIGINT, shutdown)


# =============================
# CAMERA READER
# =============================
class CameraReader:
    def __init__(self, rtsp):
        self.cap = cv2.VideoCapture(rtsp)
        self.frame = None
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while True:
            if not self.cap.isOpened():
                time.sleep(1)
                continue

            ret, frame = self.cap.read()
            if ret:
                self.frame = frame

    def get(self):
        return self.frame


# =============================
# CAMERA PROCESS
# =============================
def run_camera(camera):

    NAME = camera["name"]
    RTSP = camera["rtsp"]

    print(f"🚀 START CAMERA: {NAME}")

    model = YOLO("yolo11n.pt")
    helmet_model = YOLO("helmet.pt")

    try:
        model.to("cuda")
        helmet_model.to("cuda")
        print("⚡ GPU MODE")
    except:
        print("🐢 CPU MODE")

    model.fuse()

    reader = CameraReader(RTSP)
    session = requests.Session()

    IN, OUT = 0, 0

    history = {}
    track_time = {}
    helmet_history = {}
    last_cross = {}

    TIMEOUT = 5
    COOLDOWN = 1.5

    line_position = 0.5
    direction = "NORMAL"

    last_fetch = 0
    last_frame = 0

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
        # FETCH CONFIG (LOW LOAD)
        # =============================
        if now - last_fetch > 1:
            try:
                line_position = session.get(
                    f"http://127.0.0.1:8000/line/{cam}", timeout=1
                ).json().get("position", 0.5)

                direction = session.get(
                    f"http://127.0.0.1:8000/direction/{cam}", timeout=1
                ).json().get("mode", "NORMAL").upper()

                if direction not in ["NORMAL", "REVERSE"]:
                    direction = "NORMAL"

            except:
                pass

            last_fetch = now

        line_x = int(w * line_position)
        cv2.line(frame, (line_x, 0), (line_x, h), (0, 0, 255), 2)

        # =============================
        # TRACK OBJECT
        # =============================
        results = model.track(
            frame,
            persist=True,
            conf=0.3,
            tracker="bytetrack.yaml",
            verbose=False
        )

        if results[0].boxes.id is not None:

            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()

            for box, tid, cls in zip(boxes, ids, classes):

                if int(cls) != 0:
                    continue

                tid = int(tid)
                x1, y1, x2, y2 = map(int, box)

                if (x2 - x1) < 35:
                    continue

                cx = (x1 + x2) // 2
                track_time[tid] = now

                # =============================
                # HELMET (ONCE PER ID)
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

                    helmet_history[tid] = helmet

                # =============================
                # ZONE DETECTION
                # =============================
                zone = "LEFT" if cx < line_x else "RIGHT"

                if tid not in history:
                    history[tid] = {"zone": zone, "counted": False}
                    continue

                prev = history[tid]["zone"]
                history[tid]["zone"] = zone

                # RESET IF ID EXPIRED
                if history[tid]["counted"]:
                    continue

                # COOLDOWN ANTI SPAM
                if tid in last_cross and now - last_cross[tid] < COOLDOWN:
                    continue

                helmet = helmet_history.get(tid, False)

                # =============================
                # CROSSING LOGIC
                # =============================
                if prev == "LEFT" and zone == "RIGHT":

                    history[tid]["counted"] = True

                    if direction == "NORMAL":
                        OUT += 1
                        update_daily_counter(NAME, 0, 1)

                        save_detection(NAME,
                            "helmet_out" if helmet else "no_helmet_out",
                            1.0, "OUT")

                    else:
                        IN += 1
                        update_daily_counter(NAME, 1, 0)

                        save_detection(NAME,
                            "helmet_in" if helmet else "no_helmet_in",
                            1.0, "IN")

                    last_cross[tid] = now

                elif prev == "RIGHT" and zone == "LEFT":

                    history[tid]["counted"] = True

                    if direction == "NORMAL":
                        IN += 1
                        update_daily_counter(NAME, 1, 0)

                        save_detection(NAME,
                            "helmet_in" if helmet else "no_helmet_in",
                            1.0, "IN")

                    else:
                        OUT += 1
                        update_daily_counter(NAME, 0, 1)

                        save_detection(NAME,
                            "helmet_out" if helmet else "no_helmet_out",
                            1.0, "OUT")

                    last_cross[tid] = now

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # =============================
        # CLEAN MEMORY
        # =============================
        expired = [tid for tid, t in track_time.items() if now - t > TIMEOUT]
        for tid in expired:
            history.pop(tid, None)
            track_time.pop(tid, None)
            helmet_history.pop(tid, None)
            last_cross.pop(tid, None)

        # =============================
        # STREAM
        # =============================
        if now - last_frame > 0.1:
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
        p = multiprocessing.Process(target=run_camera, args=(cam,))
        p.start()
        processes.append(p)

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        shutdown(None, None)