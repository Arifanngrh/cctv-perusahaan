import threading
import asyncio
import psycopg2
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
# DATABASE (POSTGRESQL)
# =========================
def get_conn():
    return psycopg2.connect(
        host="127.0.0.1",
        database="cctv_db",
        user="postgres",
        password="rynnn28",
        port="5432"
    )

# =========================
# MEMORY (CONFIG + STREAM)
# =========================
line_settings = {}
direction_settings = {}

frames = {}
locks = {}

def get_lock(cam):
    if cam not in locks:
        locks[cam] = threading.Lock()
    return locks[cam]

# =========================
# SUMMARY (REAL DB)
# =========================
@app.get("/summary")
def summary():
    try:
        conn = get_conn()
        cursor = conn.cursor()

        # IN / OUT
        cursor.execute("""
        SELECT 
            COALESCE(SUM(total_in),0),
            COALESCE(SUM(total_out),0)
        FROM daily_counter
        WHERE counter_date = CURRENT_DATE
        """)
        result = cursor.fetchone()

        # HELMET
        cursor.execute("""
        SELECT
            SUM(CASE WHEN label = 'helmet' THEN 1 ELSE 0 END),
            SUM(CASE WHEN label = 'no_helmet' THEN 1 ELSE 0 END)
        FROM detections
        WHERE DATE(created_at) = CURRENT_DATE
        """)
        helmet = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            "total_in": result[0],
            "total_out": result[1],
            "total_helmet": helmet[0] or 0,
            "total_no_helmet": helmet[1] or 0,
            "current_inside": result[0] - result[1]
        }

    except Exception as e:
        print("❌ SUMMARY ERROR:", e)
        return {}

# =========================
# STATS (PER HARI)
# =========================
@app.get("/stats")
def stats():
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT 
            DATE(created_at),
            SUM(CASE WHEN direction = 'IN' THEN 1 ELSE 0 END),
            SUM(CASE WHEN direction = 'OUT' THEN 1 ELSE 0 END),
            SUM(CASE WHEN label = 'helmet' THEN 1 ELSE 0 END),
            SUM(CASE WHEN label = 'no_helmet' THEN 1 ELSE 0 END)
        FROM detections
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at)
        """)

        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        return [
            {
                "date": str(r[0]),
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
# LINE CONFIG
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
# DIRECTION CONFIG
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
# FRAME UPLOAD
# =========================
@app.post("/frame/{camera}")
async def upload(camera: str, file: UploadFile = File(...)):
    camera = unquote(camera)
    data = await file.read()

    with get_lock(camera):
        frames[camera] = data

    return {"ok": True}

# =========================
# STREAM
# =========================
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