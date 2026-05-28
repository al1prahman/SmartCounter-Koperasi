import streamlit as st
from ultralytics import YOLO
import cv2
import numpy as np
import time
import mysql.connector
import pandas as pd
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Smart Counter Dashboard", layout="wide")
st.title("📊 Dashboard Cerdas Koperasi Merah Putih")
st.markdown("Sistem Monitoring Real-time & Analitik Konversi Pembeli")

# --- KONEKSI DATABASE ---
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

# --- FUNGSI AMBIL DATA HISTORIS (Agar tidak reset ke 0) ---
def fetch_today_stats():
    if not cursor: return 0, 0, 0
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Hitung Masuk
    cursor.execute("SELECT COUNT(*) FROM visitor_logs WHERE event_type = 'Masuk' AND DATE(created_at) = %s", (today,))
    tin = cursor.fetchone()[0]
    # Hitung Keluar
    cursor.execute("SELECT COUNT(*) FROM visitor_logs WHERE event_type = 'Keluar' AND DATE(created_at) = %s", (today,))
    tout = cursor.fetchone()[0]
    # Hitung Pembeli
    cursor.execute("SELECT COUNT(*) FROM visitor_logs WHERE event_type = 'Pembeli Baru' AND DATE(created_at) = %s", (today,))
    tbuy = cursor.fetchone()[0]
    
    return tin, tout, tbuy

def get_chart_data():
    if not cursor: return pd.DataFrame(), pd.DataFrame()
    
    # 1. Data Traffic Per Jam (Hari Ini)
    today = datetime.now().strftime('%Y-%m-%d')
    query_hour = f"SELECT HOUR(created_at) as jam, COUNT(*) as total FROM visitor_logs WHERE event_type = 'Masuk' AND DATE(created_at) = '{today}' GROUP BY jam"
    df_hour = pd.read_sql(query_hour, db)
    
    # 2. Data 7 Hari Terakhir (Pengunjung vs Pembeli)
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

# --- LOGIKA DATABASE ---
def log_to_database(track_id, event_type):
    if cursor:
        try:
            cursor.execute("INSERT INTO visitor_logs (track_id, event_type, created_at) VALUES (%s, %s, %s)", 
                           (int(track_id), event_type, datetime.now()))
            db.commit()
        except: pass

def remove_false_visitor(track_id):
    if cursor:
        try:
            cursor.execute("DELETE FROM visitor_logs WHERE track_id = %s AND event_type IN ('Masuk', 'Keluar')", (int(track_id),))
            db.commit()
        except: pass

# --- INISIALISASI SESSION STATE ---
if 'initialized' not in st.session_state:
    tin, tout, tbuy = fetch_today_stats()
    st.session_state.update({
        'initialized': True,
        'count_in': tin, 'count_out': tout, 'count_buyer': tbuy,
        'track_states': {}, 'staff_zone_timers': {}, 'cashier_zone_timers': {},
        'staff_ids': set(), 'buyer_ids': set()
    })

# --- UI: METRIK UTAMA ---
c1, c2, c3 = st.columns(3)
val_in = c1.empty()
val_buy = c2.empty()
val_rate = c3.empty()

# --- SIDEBAR & MODEL ---
st.sidebar.header("Kontrol Sistem")
run_camera = st.sidebar.checkbox("▶️ Aktifkan Kamera AI", value=False)
show_charts = st.sidebar.checkbox("📈 Tampilkan Grafik Analitik", value=True)

@st.cache_resource
def load_model():
    return YOLO('yolov8n.pt')
model = load_model()

# --- AREA VIDEO ---
st.write("### 🎥 Live Camera Stream")
_, col_vid, _ = st.columns([1, 4, 1])
FRAME_WINDOW = col_vid.empty()

# Konfigurasi Zona Asal (Hardcode sementara sebelum dibuat dinamis)
LINE_X = 640
STAFF_ZONE = np.array([[100, 100], [400, 100], [400, 400], [100, 400]], np.int32)
CASHIER_ZONE = np.array([[800, 200], [1200, 200], [1200, 600], [800, 600]], np.int32)

# --- LOOP KAMERA ---
if run_camera:
    cap = cv2.VideoCapture(0)
    cap.set(3, 1280); cap.set(4, 720) # Resolusi HD 16:9
    
    while run_camera:
        ret, frame = cap.read()
        if not ret: break
        
        # Visualisasi Zona
        cv2.line(frame, (LINE_X, 0), (LINE_X, 720), (0, 255, 255), 2)
        cv2.polylines(frame, [STAFF_ZONE], True, (255, 0, 0), 2)
        cv2.polylines(frame, [CASHIER_ZONE], True, (0, 165, 255), 2)

        results = model.track(frame, persist=True, classes=[0], verbose=False)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.int().cpu().numpy()

            for box, track_id in zip(boxes, ids):
                x1, y1, x2, y2 = map(int, box)
                cx, cy = (x1+x2)//2, (y1+y2)//2
                
                is_staff = track_id in st.session_state.staff_ids
                is_buyer = track_id in st.session_state.buyer_ids
                
                # --- LOGIKA STAF (30 Detik) ---
                if cv2.pointPolygonTest(STAFF_ZONE, (cx, cy), False) >= 0 and not is_staff:
                    if track_id not in st.session_state.staff_zone_timers:
                        st.session_state.staff_zone_timers[track_id] = time.time()
                    elif time.time() - st.session_state.staff_zone_timers[track_id] >= 30:
                        st.session_state.staff_ids.add(track_id)
                        remove_false_visitor(track_id)
                        log_to_database(track_id, "Staf Aktif")
                        st.session_state.count_in = max(0, st.session_state.count_in - 1)

                # --- LOGIKA PEMBELI (20 Detik) ---
                if cv2.pointPolygonTest(CASHIER_ZONE, (cx, cy), False) >= 0 and not is_buyer:
                    if track_id not in st.session_state.cashier_zone_timers:
                        st.session_state.cashier_zone_timers[track_id] = time.time()
                    elif time.time() - st.session_state.cashier_zone_timers[track_id] >= 20:
                        st.session_state.buyer_ids.add(track_id)
                        st.session_state.count_buyer += 1
                        log_to_database(track_id, "Pembeli Baru")

                # --- LOGIKA MASUK/KELUAR GARIS PINTU ---
                if track_id not in st.session_state.track_states:
                    st.session_state.track_states[track_id] = 'kiri' if cx < LINE_X else 'kanan'
                else:
                    if st.session_state.track_states[track_id] == 'kiri' and cx > LINE_X + 40:
                        st.session_state.count_in += 1
                        st.session_state.track_states[track_id] = 'kanan'
                        log_to_database(track_id, "Masuk")
                    elif st.session_state.track_states[track_id] == 'kanan' and cx < LINE_X - 40:
                        st.session_state.count_out += 1
                        st.session_state.track_states[track_id] = 'kiri'
                        log_to_database(track_id, "Keluar")

                # Warna Bounding Box
                color = (0, 165, 255) if is_buyer else ((255, 0, 0) if is_staff else (0, 255, 0))
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Update Metrics Real-time
        val_in.metric("Total Masuk (Hari Ini)", st.session_state.count_in)
        val_buy.metric("Total Pembeli (Hari Ini)", st.session_state.count_buyer)
        rate = round((st.session_state.count_buyer / st.session_state.count_in * 100), 1) if st.session_state.count_in > 0 else 0
        val_rate.metric("Conversion Rate", f"{rate}%")

        FRAME_WINDOW.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    cap.release()

# --- AREA GRAFIK (DI BAWAH VIDEO) ---
if show_charts:
    st.write("---")
    st.write("### 📈 Analitik Kunjungan")
    df_h, df_d = get_chart_data()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Trafik Pengunjung per Jam (Hari Ini)**")
        if not df_h.empty:
            st.line_chart(df_h.set_index('jam'))
        else: st.info("Belum ada data jam ini.")
        
    with col_b:
        st.write("**Pengunjung vs Pembeli (7 Hari Terakhir)**")
        if not df_d.empty:
            st.bar_chart(df_d.set_index('tanggal'))
        else: st.info("Data historis tidak ditemukan.")