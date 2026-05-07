import psycopg2
from datetime import datetime, date

# =========================
# KONEKSI
# =========================
def connect():
    return psycopg2.connect(
        host="127.0.0.1",
        database="cctv_db",
        user="postgres",
        password="rynnn28",
        port="5432"
    )

# =========================
# INIT TABLE
# =========================
def init_db():
    conn = connect()
    cur = conn.cursor()

    # DETECTIONS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS detections (
        id SERIAL PRIMARY KEY,
        camera TEXT,
        label TEXT,
        confidence FLOAT,
        direction TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # DAILY COUNTER (PER CAMERA)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_counter (
        camera TEXT,
        counter_date DATE,
        total_in INTEGER DEFAULT 0,
        total_out INTEGER DEFAULT 0,
        PRIMARY KEY (camera, counter_date)
    );
    """)

    conn.commit()
    cur.close()
    conn.close()

# =========================
# SAVE DETECTION
# =========================
def save_detection(camera, label, confidence, direction):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO detections (camera, label, confidence, direction, created_at)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
    """, (camera, label, confidence, direction))

    conn.commit()
    cur.close()
    conn.close()

# =========================
# UPDATE COUNTER (ANTI ERROR)
# =========================
def update_daily_counter(camera, people_in, people_out):
    today = date.today()

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO daily_counter (camera, counter_date, total_in, total_out)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (camera, counter_date)
        DO UPDATE SET
            total_in = daily_counter.total_in + %s,
            total_out = daily_counter.total_out + %s
    """, (camera, today, people_in, people_out, people_in, people_out))

    conn.commit()
    cur.close()
    conn.close()

# =========================
# SUMMARY GLOBAL (SEMUA CAMERA)
# =========================
def get_summary_today():
    today = date.today()

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            COALESCE(SUM(total_in),0),
            COALESCE(SUM(total_out),0)
        FROM daily_counter
        WHERE counter_date = %s
    """, (today,))

    res = cur.fetchone()

    cur.close()
    conn.close()

    return {
        "total_in": res[0],
        "total_out": res[1]
    }

# =========================
# HELMET STATS
# =========================
def get_helmet_stats_today():
    today = date.today()

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE label='helmet'),
            COUNT(*) FILTER (WHERE label='no_helmet')
        FROM detections
        WHERE DATE(created_at) = %s
    """, (today,))

    res = cur.fetchone()

    cur.close()
    conn.close()

    return {
        "helmet": res[0],
        "no_helmet": res[1]
    }

# =========================
# DASHBOARD FINAL
# =========================
def get_dashboard():
    summary = get_summary_today()
    helmet = get_helmet_stats_today()

    return {
        "in": summary["total_in"],
        "out": summary["total_out"],
        "helmet": helmet["helmet"],
        "no_helmet": helmet["no_helmet"]
    }

# =========================
# INIT
# =========================
if __name__ == "__main__":
    init_db()
    print("✅ Database Ready")