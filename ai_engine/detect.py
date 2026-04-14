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

# =============================
# SHUTDOWN
# =============================
def shutdown(sig, frame):
    print("🛑 Stopping AI Engine...")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# =============================
# CAMERA READER
# =============================
class CameraReader:
    def __init__(self, rtsp):
        self.rtsp = rtsp
        self.cap = None
        self.frame = None
        self.running = True

        self.connect()
        threading.Thread(target=self.update, daemon=True).start()

    def connect(self):
        if self.cap:
            self.cap.release()

        print("🔄 CONNECTING RTSP...")
        self.cap = cv2.VideoCapture(self.rtsp)

        if self.cap.isOpened():
            print("✅ RTSP CONNECTED")
        else:
            print("❌ RTSP FAILED")

    def update(self):
        while self.running:
            if not self.cap.isOpened():
                self.connect()
                time.sleep(2)
                continue

            ret, frame = self.cap.read()

            if not ret:
                self.connect()
                continue

            self.frame = frame

    def get(self):
        return self.frame

# =============================
# MAIN PROCESS
# =============================
def run_camera(camera):

    NAME = camera["name"]
    RTSP = camera["rtsp"]

    print("🚀 START CAMERA:", NAME)

    model = YOLO("yolo11n.pt")

    try:
        model.to("cuda")
        print("⚡ GPU")
    except:
        print("🐢 CPU")

    model.fuse()

    reader = CameraReader(RTSP)
    session = requests.Session()

    IN = 0
    OUT = 0

    last_sent_in = -1
    last_sent_out = -1

    history = {}
    track_time = {}

    TIMEOUT = 5
    OFFSET = 30   # 🔥 FIX (lebih kecil)
    COOLDOWN = 2
    GLOBAL_COOLDOWN = 0.3

    last_count_time = {}
    last_global_time = 0

    last_api = 0
    last_frame = 0
    last_line_fetch = 0
    last_direction_fetch = 0

    line_position = 0.65
    direction_mode = "NORMAL"

    while True:

        now = time.time()
        frame = reader.get()

        if frame is None:
            time.sleep(0.05)
            continue

        frame = cv2.resize(frame, (640, 360))
        h, w = frame.shape[:2]

        cam = quote(NAME)

        # =============================
        # GET SETTING
        # =============================
        if now - last_line_fetch > 1:
            try:
                r = session.get(f"http://127.0.0.1:8000/line/{cam}", timeout=1)
                line_position = r.json().get("position", 0.65)
            except:
                pass
            last_line_fetch = now

        if now - last_direction_fetch > 1:
            try:
                r = session.get(f"http://127.0.0.1:8000/direction/{cam}", timeout=1)
                direction_mode = r.json().get("mode", "NORMAL").upper()
            except:
                pass
            last_direction_fetch = now

        line_x = int(w * line_position)
        cv2.line(frame, (line_x, 0), (line_x, h), (0, 0, 255), 2)

        # =============================
        # YOLO TRACK
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

                # 🔥 FILTER cuma manusia
                if int(cls) != 0:
                    continue

                tid = int(tid)
                x1, y1, x2, y2 = map(int, box)

                if (x2 - x1) < 50:
                    continue

                cx = (x1 + x2) // 2

                track_time[tid] = now

                # =============================
                # ZONE DETECTION
                # =============================
                if cx < line_x - OFFSET:
                    zone = "LEFT"
                elif cx > line_x + OFFSET:
                    zone = "RIGHT"
                else:
                    zone = "MIDDLE"

                if tid not in history:
                    history[tid] = {
                        "zone": zone,
                        "counted": False
                    }
                    continue

                prev_zone = history[tid]["zone"]

                # 🔥 WAJIB UPDATE ZONE DULU
                history[tid]["zone"] = zone

                if history[tid]["counted"]:
                    continue

                # skip middle tapi tetap update
                if zone == "MIDDLE":
                    continue

                # cooldown per object
                if tid in last_count_time and now - last_count_time[tid] < COOLDOWN:
                    continue

                # global cooldown
                if now - last_global_time < GLOBAL_COOLDOWN:
                    continue

                # =============================
                # CROSSING FIXED
                # =============================
                if prev_zone in ["LEFT", "MIDDLE"] and zone == "RIGHT":

                    if direction_mode == "NORMAL":
                        OUT += 1
                        print("➡️ OUT:", OUT)
                    else:
                        IN += 1
                        print("⬅️ IN:", IN)

                    history[tid]["counted"] = True
                    last_count_time[tid] = now
                    last_global_time = now

                elif prev_zone in ["RIGHT", "MIDDLE"] and zone == "LEFT":

                    if direction_mode == "NORMAL":
                        IN += 1
                        print("⬅️ IN:", IN)
                    else:
                        OUT += 1
                        print("➡️ OUT:", OUT)

                    history[tid]["counted"] = True
                    last_count_time[tid] = now
                    last_global_time = now

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
                cv2.putText(frame, f"ID {tid}", (x1, y1-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

        # =============================
        # CLEAN MEMORY
        # =============================
        expired = [tid for tid, t in track_time.items() if now - t > TIMEOUT]
        for tid in expired:
            history.pop(tid, None)
            track_time.pop(tid, None)
            last_count_time.pop(tid, None)

        # =============================
        # SEND API
        # =============================
        if now - last_api > 1:

            if IN != last_sent_in or OUT != last_sent_out:
                try:
                    session.post(API_URL, json={
                        "camera": NAME,
                        "people_in": IN,
                        "people_out": OUT
                    }, timeout=1)

                    print("📊 SENT:", IN, OUT)

                    last_sent_in = IN
                    last_sent_out = OUT

                except:
                    pass

            last_api = now

        # =============================
        # STREAM
        # =============================
        if now - last_frame > 0.2:
            try:
                ret, jpg = cv2.imencode(".jpg", frame)
                if ret:
                    session.post(
                        f"{STREAM_URL}/{cam}",
                        files={"file": ("frame.jpg", jpg.tobytes(), "image/jpeg")},
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

    processes = []

    for cam in config["cameras"]:
        p = multiprocessing.Process(target=run_camera, args=(cam,))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()