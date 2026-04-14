import threading
import asyncio
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import date
from urllib.parse import unquote

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# MEMORY STORAGE
# =========================
camera_totals = {}
last_date = date.today()

line_settings = {}
direction_settings = {}

# =========================
# MODEL
# =========================
class Counter(BaseModel):
    camera: str
    people_in: int
    people_out: int
    helmet: int
    no_helmet: int

# =========================
# SAVE COUNTER (FIX ANTI SPAM)
# =========================
@app.post("/counter")
def save(data: Counter):

    global last_date

    today = date.today()

    # reset tiap hari
    if today != last_date:
        camera_totals.clear()
        last_date = today

    key = data.camera

    # 🔥 SIMPAN PER CAMERA (BUKAN TAMBAH)
    camera_totals[key] = {
        "in": data.people_in,
        "out": data.people_out,
        "helmet": data.helmet,
        "no_helmet": data.no_helmet
    }

    print("📊 UPDATE:", key, camera_totals[key])

    return {"status": "ok"}


# =========================
# SUMMARY
# =========================
@app.get("/summary")
def summary():

    total_in = sum(cam["in"] for cam in camera_totals.values())
    total_out = sum(cam["out"] for cam in camera_totals.values())
    total_helmet = sum(cam["helmet"] for cam in camera_totals.values())
    total_no_helmet = sum(cam["no_helmet"] for cam in camera_totals.values())

    return {
        "total_in": total_in,
        "total_out": total_out,
        "total_helmet": total_helmet,
        "total_no_helmet": total_no_helmet,
        "current_inside": total_in - total_out
    }


# =========================
# LINE CONTROL
# =========================
@app.post("/line/{camera}")
def set_line(camera: str, data: dict):

    camera = unquote(camera)
    position = float(data.get("position", 0.5))

    position = max(0.1, min(0.9, position))
    line_settings[camera] = position

    return {"camera": camera, "position": position}


@app.get("/line/{camera}")
def get_line(camera: str):

    camera = unquote(camera)

    return {
        "camera": camera,
        "position": line_settings.get(camera, 0.5)
    }


# =========================
# DIRECTION CONTROL
# =========================
@app.post("/direction/{camera}")
def set_direction(camera: str, data: dict):

    camera = unquote(camera)
    mode = data.get("mode", "NORMAL").upper()

    if mode not in ["NORMAL", "REVERSE"]:
        mode = "NORMAL"

    direction_settings[camera] = mode

    return {"camera": camera, "mode": mode}


@app.get("/direction/{camera}")
def get_direction(camera: str):

    camera = unquote(camera)

    return {
        "camera": camera,
        "mode": direction_settings.get(camera, "NORMAL")
    }


# =========================
# STREAM SYSTEM
# =========================
frames = {}
locks = {}

def get_lock(cam):
    if cam not in locks:
        locks[cam] = threading.Lock()
    return locks[cam]


@app.post("/frame/{camera}")
async def upload(camera: str, file: UploadFile = File(...)):

    camera = unquote(camera)
    data = await file.read()

    with get_lock(camera):
        frames[camera] = data

    return {"ok": True}


@app.get("/stream/{camera}")
async def stream(camera: str, request: Request):

    camera = unquote(camera)

    async def gen():
        while True:

            if await request.is_disconnected():
                break

            with get_lock(camera):
                frame = frames.get(camera)

            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame +
                    b"\r\n"
                )

            await asyncio.sleep(0.03)

    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )