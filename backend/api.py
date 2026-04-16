import threading
import asyncio
import sqlite3
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import date, datetime
from urllib.parse import unquote

app = FastAPI()

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# DATABASE (ANTI LOCK FIX)
# =========================
conn = sqlite3.connect("cctv.db", check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL;")  # 🔥 anti lock
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera TEXT,
    date TEXT,
    people_in INTEGER,
    people_out INTEGER,
    helmet INTEGER,
    no_helmet INTEGER
)
""")
conn.commit()

# =========================
# MEMORY (REALTIME)
# =========================
camera_totals = {}
last_date = date.today()

line_settings = {}
direction_settings = {}

frames = {}
locks = {}

def get_lock(cam):
    if cam not in locks:
        locks[cam] = threading.Lock()
    return locks[cam]

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
# COUNTER (REALTIME + DB)
# =========================
@app.post("/counter")
def save(data: Counter):
    global last_date

    today = date.today()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # reset realtime tiap hari
    if today != last_date:
        camera_totals.clear()
        last_date = today

    # =====================
    # REALTIME
    # =====================
    camera_totals[data.camera] = {
        "in": data.people_in,
        "out": data.people_out,
        "helmet": data.helmet,
        "no_helmet": data.no_helmet
    }

    # =====================
    # DATABASE (UPSERT)
    # =====================
    try:
        cursor.execute("""
        SELECT id FROM stats WHERE camera=? AND date=?
        """, (data.camera, today_str))

        row = cursor.fetchone()

        if row:
            cursor.execute("""
            UPDATE stats SET
            people_in=?,
            people_out=?,
            helmet=?,
            no_helmet=?
            WHERE id=?
            """, (
                data.people_in,
                data.people_out,
                data.helmet,
                data.no_helmet,
                row[0]
            ))
        else:
            cursor.execute("""
            INSERT INTO stats (camera, date, people_in, people_out, helmet, no_helmet)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data.camera,
                today_str,
                data.people_in,
                data.people_out,
                data.helmet,
                data.no_helmet
            ))

        conn.commit()

    except Exception as e:
        print("❌ DB ERROR:", e)

    return {"ok": True}

# =========================
# SUMMARY (REALTIME)
# =========================
@app.get("/summary")
def summary():
    return {
        "total_in": sum(c["in"] for c in camera_totals.values()),
        "total_out": sum(c["out"] for c in camera_totals.values()),
        "total_helmet": sum(c["helmet"] for c in camera_totals.values()),
        "total_no_helmet": sum(c["no_helmet"] for c in camera_totals.values()),
        "current_inside": sum(c["in"] for c in camera_totals.values()) - sum(c["out"] for c in camera_totals.values())
    }

# =========================
# STATS (DASHBOARD)
# =========================
@app.get("/stats")
def stats():
    try:
        cursor.execute("""
        SELECT date,
               SUM(people_in),
               SUM(people_out),
               SUM(helmet),
               SUM(no_helmet)
        FROM stats
        GROUP BY date
        ORDER BY date
        """)

        rows = cursor.fetchall()

        return [
            {
                "date": r[0],
                "in": r[1],
                "out": r[2],
                "helmet": r[3],
                "no_helmet": r[4]
            }
            for r in rows
        ]

    except Exception as e:
        print("❌ STATS ERROR:", e)
        return []

# =========================
# LINE
# =========================
@app.post("/line/{camera}")
def set_line(camera: str, data: dict):
    camera = unquote(camera)
    pos = float(data.get("position", 0.5))
    pos = max(0.1, min(0.9, pos))
    line_settings[camera] = pos

    print("📏 LINE:", camera, pos)
    return {"position": pos}

@app.get("/line/{camera}")
def get_line(camera: str):
    camera = unquote(camera)
    return {"position": line_settings.get(camera, 0.5)}

# =========================
# DIRECTION
# =========================
@app.post("/direction/{camera}")
def set_direction(camera: str, data: dict):
    camera = unquote(camera)
    mode = data.get("mode", "NORMAL").upper()

    if mode == "REVERSED":
        mode = "REVERSE"

    if mode not in ["NORMAL", "REVERSE"]:
        mode = "NORMAL"

    direction_settings[camera] = mode

    print("🔄 DIRECTION:", camera, mode)
    return {"mode": mode}

@app.get("/direction/{camera}")
def get_direction(camera: str):
    camera = unquote(camera)
    return {"mode": direction_settings.get(camera, "NORMAL")}

# =========================
# STREAM
# =========================
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
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )

            await asyncio.sleep(0.03)

    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )