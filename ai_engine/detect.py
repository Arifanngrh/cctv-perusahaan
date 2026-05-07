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

from database import update_daily_counter, save_detection

# ================= RTSP STABILITY =================
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"
    "stimeout;3000000|"
    "max_delay;500000|"
    "buffer_size;102400"
)

API_URL = "http://127.0.0.1:8000"

processes = []
GLOBAL_COOLDOWN = {}




# ================= STOP ALL =================
def shutdown(sig, frame):
    print("\n🛑 STOP ALL CAMERA PROCESS")
    for p in processes:
        if p.is_alive():
            p.terminate()
    os._exit(0)


signal.signal(signal.SIGINT, shutdown)


# ================= CAMERA READER =================
class CameraReader:
    def __init__(self, rtsp):
        self.rtsp = rtsp
        self.cap = self.connect()
        self.frame = None
        self.lock = threading.Lock()
        threading.Thread(target=self.update, daemon=True).start()

    def connect(self):
        print("🔄 Connecting RTSP...")
        cap = cv2.VideoCapture(self.rtsp, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def update(self):
        while True:
            ret, frame = self.cap.read()

            if not ret or frame is None:
                print("⚠ Frame rusak / timeout, reconnect...")
                self.cap.release()
                time.sleep(3)
                self.cap = self.connect()
                continue

            with self.lock:
                self.frame = frame

    def get(self):
        with self.lock:
            return self.frame


# ================= CAMERA PROCESS =================
def run_camera(camera):
    NAME = camera["name"].strip()
    RTSP = camera["rtsp"]

    print(f"START CAMERA: {NAME}")

    BASE = os.path.dirname(__file__)
    model = YOLO(os.path.join(BASE, "yolo11n.pt"))
    helmet_model = YOLO(os.path.join(BASE, "helmet.pt"))

    try:
        model.to("cuda")
        helmet_model.to("cuda")
        print(f"⚡ {NAME} GPU MODE")
    except:
        print(f"{NAME} CPU MODE")

    reader = CameraReader(RTSP)
    session = requests.Session()

    history = {}
    track_time = {}
    helmet_history = {}

    TIMEOUT = 10

    line_position = 0.5
    direction = "NORMAL"

    last_fetch = 0
    last_frame = 0

    while True:
        now = time.time()
        frame = reader.get()

        if frame is None or frame.size == 0:
            continue

        frame = cv2.resize(frame, (960, 540))
        h, w = frame.shape[:2]

        cam = quote(NAME)

        # ================= FETCH CONFIG =================
        if now - last_fetch > 2:
            try:
                line_position = session.get(
                    f"{API_URL}/line/{cam}", timeout=2
                ).json().get("position", 0.5)

                direction = session.get(
                    f"{API_URL}/direction/{cam}", timeout=2
                ).json().get("mode", "NORMAL")

            except Exception as e:
                print("⚠ CONFIG ERROR:", e)

            last_fetch = now

        line_y = int(h * line_position)
        # marker kiri
        cv2.circle(frame, (20, line_y), 8, (0, 0, 255), -1)

        # marker kanan
        cv2.circle(frame, (w - 20, line_y), 8, (0, 0, 255), -1)

        # ================= YOLO DETECT PERSON ONLY =================
        results = model.track(
            frame,
            persist=True,
            conf=0.1,
            iou=0.5,
            imgsz=640,
            tracker="bytetrack.yaml",
            verbose=False
        )

        if results and len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()
            ids = results[0].boxes.id
            ids = ids.cpu().numpy() if ids is not None else [None] * len(boxes)

            for box, tid, cls in zip(boxes, ids, classes):

                # class 0 = person
                if int(cls) != 0:
                    continue

                x1, y1, x2, y2 = map(int, box)

                # filter object terlalu kecil
                if (x2 - x1) < 40 or (y2 - y1) < 80:
                    continue

                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                if tid is None:
                    tid = f"{cx // 50}_{cy // 50}"
                else:
                    tid = int(tid)

                track_time[tid] = now

                # ================= HELMET CHECK =================
                if tid not in helmet_history:
                    try:
                        crop = frame[y1:y2, x1:x2]
                        SAVE_DIR = os.path.join(BASE, "dataset_collect", NAME)
                        os.makedirs(SAVE_DIR, exist_ok=True)

                        if int(now) % 3 == 0:
                            filename = f"{int(now)}_{tid}.jpg"
                            cv2.imwrite(os.path.join(SAVE_DIR, filename), crop)
                        helmet = False

                        res = helmet_model(crop, conf=0.6, verbose=False)

                        for r in res:
                            for c in r.boxes.cls:
                                if int(c) == 0:
                                    helmet = True

                        helmet_history[tid] = helmet

                    except Exception as e:
                        print("⚠ HELMET ERROR:", e)
                        helmet_history[tid] = False

                helmet = helmet_history.get(tid, False)

                

                # ================= VISUAL BOUNDING BOX =================
                color = (0, 255, 0) if helmet else (0, 0, 255)
                label = "HELMET" if helmet else "NO HELMET"

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                cv2.putText(
                    frame,
                    f"{label} ID:{tid}",
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2
                )

                # ================= CROSSING LINE =================
                zone = "TOP" if cy < line_y else "BOTTOM"

                if tid not in history:
                    history[tid] = {"zone": zone, "counted": False}
                    continue

                prev = history[tid]["zone"]
                history[tid]["zone"] = zone

                if history[tid]["counted"] and now - history[tid].get("counted_at", 0) < 10:
                    continue
                else:
                    history[tid]["counted"] = False

                key_cross = f"{NAME}_{tid}"

                if key_cross in GLOBAL_COOLDOWN and now - GLOBAL_COOLDOWN[key_cross] < 1:
                    continue

                if prev != zone:
                    history[tid]["counted"] = True
                    history[tid]["counted_at"] = now

                    direction_type = "IN" if zone == "TOP" else "OUT"

                    if direction == "REVERSE":
                        direction_type = "OUT" if direction_type == "IN" else "IN"

                    try:
                        print("🚶 CROSSING:", NAME, tid, direction_type)

                        update_daily_counter(
                            NAME,
                            1 if direction_type == "IN" else 0,
                            1 if direction_type == "OUT" else 0
                        )

                        save_detection(
                            NAME,
                            "helmet" if helmet else "no_helmet",
                            1.0,
                            direction_type
                        )

                    except Exception as e:
                        print("❌ DB CROSS ERROR:", e)

                    GLOBAL_COOLDOWN[key_cross] = now

        # ================= CLEAN MEMORY =================
        expired = [tid for tid, t in track_time.items() if now - t > TIMEOUT]

        for tid in expired:
            history.pop(tid, None)
            track_time.pop(tid, None)
            helmet_history.pop(tid, None)
            GLOBAL_COOLDOWN.pop(f"{NAME}_{tid}", None)

        # ================= SEND FRAME TO API =================
        if now - last_frame > 0.02:
            try:
                _, jpg = cv2.imencode(
                    ".jpg",
                    frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 70]
                )

                session.post(
                    f"{API_URL}/frame/{cam}",
                    files={"file": ("f.jpg", jpg.tobytes())},
                    timeout=2
                )

            except Exception as e:
                print("❌ STREAM ERROR:", e)

            last_frame = now


# ================= START ALL CAMERA =================
if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), "config.json")

    with open(config_path, "r") as f:
        cameras = json.load(f).get("cameras", [])

    if not cameras:
        print("❌ Tidak ada kamera di config.json")
        sys.exit(1)

    print(f"✅ Total camera: {len(cameras)}")

    for camera in cameras:
        p = multiprocessing.Process(target=run_camera, args=(camera,))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()