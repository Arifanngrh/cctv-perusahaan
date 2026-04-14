import psycopg2
from datetime import date


def connect():
    return psycopg2.connect(
        host="localhost",
        database="cctv_db",
        user="postgres",
        password="salatiga17",
        port="5432"
    )


# =========================
# UPSERT DAILY COUNTER
# =========================
def upsert_daily(camera, people_in, people_out):

    today = date.today()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO daily_counter (camera, counter_date, total_in, total_out)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (camera, counter_date)
        DO UPDATE SET
            total_in = EXCLUDED.total_in,
            total_out = EXCLUDED.total_out
    """, (camera, today, people_in, people_out))

    conn.commit()
    cursor.close()
    conn.close()


# =========================
# GET TODAY PER CAMERA
# =========================
def get_today(camera):

    today = date.today()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT camera, counter_date, total_in, total_out
        FROM daily_counter
        WHERE camera = %s AND counter_date = %s
    """, (camera, today))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row


# =========================
# GET SUMMARY TODAY
# =========================
def get_summary_today():

    today = date.today()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(total_in),0),
               COALESCE(SUM(total_out),0)
        FROM daily_counter
        WHERE counter_date = %s
    """, (today,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row