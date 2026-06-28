import streamlit as st
import mysql.connector
import pandas as pd
import numpy as np
from datetime import datetime

@st.cache_resource
def init_connection():
    try:
        return mysql.connector.connect(
            host="localhost", user="root", password="", database="koperasi_db"
        )
    except Exception:
        return None

db = init_connection()
cursor = db.cursor() if db else None

def fetch_today_stats():
    if not cursor: return 0, 0, 0
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM visitor_logs WHERE event_type = 'Masuk' AND DATE(created_at) = %s", (today,))
    tin = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM visitor_logs WHERE event_type = 'Keluar' AND DATE(created_at) = %s", (today,))
    tout = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM visitor_logs WHERE event_type = 'Pembeli Baru' AND DATE(created_at) = %s", (today,))
    tbuy = cursor.fetchone()[0]
    return tin, tout, tbuy

def get_chart_data():
    if not cursor: return pd.DataFrame(), pd.DataFrame()
    today = datetime.now().strftime('%Y-%m-%d')
    query_hour = f"SELECT HOUR(created_at) as jam, COUNT(*) as total FROM visitor_logs WHERE event_type = 'Masuk' AND DATE(created_at) = '{today}' GROUP BY jam"
    df_hour = pd.read_sql(query_hour, db)
    
    query_days = """
        SELECT DATE(created_at) as tanggal, 
        SUM(CASE WHEN event_type = 'Masuk' THEN 1 ELSE 0 END) as Pengunjung,
        SUM(CASE WHEN event_type = 'Pembeli Baru' THEN 1 ELSE 0 END) as Pembeli
        FROM visitor_logs 
        WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        GROUP BY tanggal ORDER BY tanggal ASC
    """
    df_days = pd.read_sql(query_days, db)
    return df_hour, df_days

def get_export_data(start_date, end_date):
    if not cursor: return pd.DataFrame()
    query = """
        SELECT 
            DATE(created_at) as Tanggal,
            SUM(CASE WHEN event_type = 'Masuk' THEN 1 ELSE 0 END) as 'Total Pengunjung',
            SUM(CASE WHEN event_type = 'Pembeli Baru' THEN 1 ELSE 0 END) as 'Total Pembeli',
            SUM(CASE WHEN event_type = 'Staf Aktif' THEN 1 ELSE 0 END) as 'Jumlah Staf'
        FROM visitor_logs
        WHERE DATE(created_at) >= %s AND DATE(created_at) <= %s
        GROUP BY Tanggal
        ORDER BY Tanggal ASC
    """
    cursor.execute(query, (start_date, end_date))
    rows = cursor.fetchall()
    cols = ['Tanggal', 'Total Pengunjung', 'Total Pembeli', 'Jumlah Staf']
    df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df['Tingkat Konversi (%)'] = (df['Total Pembeli'] / df['Total Pengunjung'] * 100).fillna(0).round(1)
        df['Tingkat Konversi (%)'] = df['Tingkat Konversi (%)'].replace([np.inf, -np.inf], 0)
    return df

def log_to_database(track_id, event_type):
    if cursor:
        try:
            cursor.execute("INSERT INTO visitor_logs (track_id, event_type, created_at) VALUES (%s, %s, %s)", 
                           (int(track_id), event_type, datetime.now()))
            db.commit()
        except: pass

def add_log(track_id, event, zone, duration="-"):
    time_str = datetime.now().strftime("%H:%M:%S")
    st.session_state.recent_logs.insert(0, {"time": time_str, "id": f"#{track_id:04d}", "event": event, "zone": zone, "duration": duration})
    if len(st.session_state.recent_logs) > 6: st.session_state.recent_logs.pop()