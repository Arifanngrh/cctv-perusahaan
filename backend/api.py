from fastapi import FastAPI, UploadFile, File, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import threading, asyncio, psycopg2, json, os
from urllib.parse import unquote

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../ai_engine/config.json")

def load_cameras():
    with open(CONFIG_PATH) as f:
        return json.load(f).get("cameras", [])

def get_conn():
    return psycopg2.connect(
        host="127.0.0.1",
        database="cctv_db",
        user="postgres",
        password="rynnn28",
        port="5432"
    )

line_settings = {}
direction_settings = {}
frames = {}

@app.get("/cameras")
def cams():
    return load_cameras()

# ✅ FINAL SUMMARY
@app.get("/summary")
def summary():
    conn = get_conn()
    cur = conn.cursor()

    # IN / OUT dari daily_counter
    cur.execute("""
        SELECT COALESCE(SUM(total_in),0), COALESCE(SUM(total_out),0)
        FROM daily_counter
        WHERE counter_date = CURRENT_DATE
    """)
    res = cur.fetchone()

    # HELMET dari detections
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE label='helmet'),
            COUNT(*) FILTER (WHERE label='no_helmet')
        FROM detections
        WHERE created_at >= CURRENT_DATE
    """)
    helmet = cur.fetchone()

    conn.close()

    return {
        "total_in": res[0] or 0,
        "total_out": res[1] or 0,
        "total_helmet": helmet[0] or 0,
        "total_no_helmet": helmet[1] or 0
    }

@app.get("/realtime")
def realtime():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT 
        date_trunc('minute', created_at) AS time_bucket,
        COALESCE(COUNT(*) FILTER (WHERE direction='IN'), 0) AS in_count,
        COALESCE(COUNT(*) FILTER (WHERE direction='OUT'), 0) AS out_count,
        COALESCE(COUNT(*) FILTER (WHERE label='helmet'), 0) AS helmet,
        COALESCE(COUNT(*) FILTER (WHERE label='no_helmet'), 0) AS no_helmet
    FROM detections
    WHERE created_at >= NOW() - INTERVAL '30 minutes'
      AND direction IN ('IN', 'OUT')
    GROUP BY time_bucket
    ORDER BY time_bucket ASC
    LIMIT 30
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "time": str(r[0]),
            "in": r[1] or 0,
            "out": r[2] or 0,
            "helmet": r[3] or 0,
            "no_helmet": r[4] or 0
        }
        for r in rows
    ]

@app.get("/stats")
def stats():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT DATE(created_at),
    COUNT(*) FILTER (WHERE direction='IN'),
    COUNT(*) FILTER (WHERE direction='OUT'),
    COUNT(*) FILTER (WHERE label='helmet'),
    COUNT(*) FILTER (WHERE label='no_helmet')
    FROM detections
    GROUP BY 1 ORDER BY 1
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {"date": str(r[0]), "in": r[1], "out": r[2], "helmet": r[3], "no_helmet": r[4]}
        for r in rows
    ]

@app.post("/line/{camera}")
def set_line(camera: str, data: dict = Body(...)):
    line_settings[unquote(camera)] = float(data.get("position", 0.5))
    return {"ok": True}

@app.get("/line/{camera}")
def get_line(camera: str):
    return {"position": line_settings.get(unquote(camera), 0.5)}

@app.post("/direction/{camera}")
def set_dir(camera: str, data: dict = Body(...)):
    direction_settings[unquote(camera)] = data.get("mode", "NORMAL")
    return {"ok": True}

@app.get("/direction/{camera}")
def get_dir(camera: str):
    return {"mode": direction_settings.get(unquote(camera), "NORMAL")}

@app.post("/frame/{camera}")
async def upload(camera: str, file: UploadFile = File(...)):
    frames[unquote(camera)] = await file.read()
    return {"ok": True}



@app.get("/stream/{camera}")
async def stream(camera: str, request: Request):
    camera = unquote(camera)

    async def gen():
        while True:
            if await request.is_disconnected():
                break

            frame = frames.get(camera)
            if frame:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"

            await asyncio.sleep(0.03)
            


    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")