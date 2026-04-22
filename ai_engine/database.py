import psycopg2
from datetime import datetime, date


# =========================
# KONEKSI DATABASE
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
# AUTO CREATE TABLE (ANTI ERROR)
# =========================
def init_db():
    conn = connect()
    cursor = conn.cursor()

    # 🔥 detections
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detections (
        id SERIAL PRIMARY KEY,
        camera TEXT,
        label TEXT,
        confidence FLOAT,
        direction TEXT,
        created_at TIMESTAMP
    );
    """)

    # 🔥 daily counter
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_counter (
        id SERIAL PRIMARY KEY,
        camera TEXT,
        counter_date DATE,
        total_in INTEGER DEFAULT 0,
        total_out INTEGER DEFAULT 0,
        UNIQUE(camera, counter_date)
    );
    """)

    conn.commit()
    cursor.close()
    conn.close()


# =========================
# SIMPAN RAW DETECTION
# =========================
def save_detection(camera, label, confidence, direction):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO detections (camera, label, confidence, direction, created_at)
        VALUES (%s, %s, %s, %s, %s)
    """, (camera, label, confidence, direction, datetime.now()))

    conn.commit()
    cursor.close()
    conn.close()


# =========================
# UPDATE DAILY COUNTER
# =========================
def update_daily_counter(camera, people_in, people_out):

    today = date.today()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO daily_counter (camera, counter_date, total_in, total_out)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (camera, counter_date)
        DO UPDATE SET
            total_in = daily_counter.total_in + EXCLUDED.total_in,
            total_out = daily_counter.total_out + EXCLUDED.total_out
    """, (camera, today, people_in, people_out))

    conn.commit()
    cursor.close()
    conn.close()


# =========================
# GET SUMMARY HARI INI
# =========================
def get_summary_today():
    today = date.today()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            COALESCE(SUM(total_in), 0),
            COALESCE(SUM(total_out), 0)
        FROM daily_counter
        WHERE counter_date = %s
    """, (today,))

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "total_in": result[0],
        "total_out": result[1]
    }


# =========================
# GET HELMET STATS
# =========================
def get_helmet_stats_today():
    today = date.today()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN label = 'helmet' THEN 1 ELSE 0 END),0),
            COALESCE(SUM(CASE WHEN label = 'no_helmet' THEN 1 ELSE 0 END),0)
        FROM detections
        WHERE DATE(created_at) = %s
    """, (today,))

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "helmet": result[0],
        "no_helmet": result[1]
    }


# =========================
# DASHBOARD
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
# INIT AUTO
# =========================
if __name__ == "__main__":
    init_db()
    print("✅ Database Ready")