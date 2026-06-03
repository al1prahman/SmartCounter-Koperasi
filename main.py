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

# --- FUNGSI AMBIL DATA HISTORIS ---
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
cam_index = st.sidebar.number_input("Pilih ID Kamera (0=Bawaan, 1=Eksternal)", min_value=0, max_value=5, value=0)

# === PENGATURAN ZONA & DURASI DINAMIS ===
with st.sidebar.expander("⚙️ Konfigurasi Garis & Zona", expanded=False):
    st.markdown("**Durasi Konversi (Detik)**")
    STAFF_LIMIT = st.slider("Waktu Tunggu Staf", 1, 60, 10) # Default diubah ke 10 detik
    BUYER_LIMIT = st.slider("Waktu Tunggu Pembeli", 1, 60, 10) # Default diubah ke 10 detik

    st.markdown("**Garis Pintu (Masuk/Keluar)**")
    LINE_X = st.slider("Posisi Garis Pintu", 0, 640, 320)
    
    st.markdown("**Zona Staf (Biru)**")
    stf_x = st.slider("Staf: Posisi Kiri/Kanan (X)", 0, 640, 50)
    stf_y = st.slider("Staf: Posisi Atas/Bawah (Y)", 0, 480, 50)
    stf_w = st.slider("Staf: Lebar Kotak", 50, 640, 200)
    stf_h = st.slider("Staf: Tinggi Kotak", 50, 480, 300)
    STAFF_ZONE = np.array([[stf_x, stf_y], [stf_x+stf_w, stf_y], [stf_x+stf_w, stf_y+stf_h], [stf_x, stf_y+stf_h]], np.int32)
    
    st.markdown("**Zona Kasir (Oranye)**")
    ksr_x = st.slider("Kasir: Posisi Kiri/Kanan (X)", 0, 640, 380)
    ksr_y = st.slider("Kasir: Posisi Atas/Bawah (Y)", 0, 480, 50)
    ksr_w = st.slider("Kasir: Lebar Kotak", 50, 640, 200)
    ksr_h = st.slider("Kasir: Tinggi Kotak", 50, 480, 300)
    CASHIER_ZONE = np.array([[ksr_x, ksr_y], [ksr_x+ksr_w, ksr_y], [ksr_x+ksr_w, ksr_y+ksr_h], [ksr_x, ksr_y+ksr_h]], np.int32)

@st.cache_resource
def load_model():
    return YOLO('yolo11n.pt')
model = load_model()

# --- AREA VIDEO ---
st.write("### 🎥 Live Camera Stream")
_, col_vid, _ = st.columns([1, 4, 1])
FRAME_WINDOW = col_vid.empty()

# --- LOOP KAMERA ---
if run_camera:
    cap = cv2.VideoCapture(cam_index)
    cap.set(3, 640); cap.set(4, 480) 
    
    while run_camera:
        ret, frame = cap.read()
        if not ret: break
        
        cv2.line(frame, (LINE_X, 0), (LINE_X, 480), (0, 255, 255), 2)
        cv2.polylines(frame, [STAFF_ZONE], True, (255, 0, 0), 2)
        cv2.putText(frame, "ZONA STAF", (STAFF_ZONE[0][0], STAFF_ZONE[0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        cv2.polylines(frame, [CASHIER_ZONE], True, (0, 165, 255), 2)
        cv2.putText(frame, "ZONA KASIR", (CASHIER_ZONE[0][0], CASHIER_ZONE[0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

        results = model.track(frame, persist=True, classes=[0], verbose=False, conf=0.5, imgsz=320)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.int().cpu().numpy()

            for box, track_id in zip(boxes, ids):
                x1, y1, x2, y2 = map(int, box)
                cx, cy = (x1+x2)//2, (y1+y2)//2
                
                is_staff = track_id in st.session_state.staff_ids
                is_buyer = track_id in st.session_state.buyer_ids
                
                # --- LOGIKA STAF (Dinamis) ---
                if cv2.pointPolygonTest(STAFF_ZONE, (cx, cy), False) >= 0 and not is_staff:
                    if track_id not in st.session_state.staff_zone_timers:
                        st.session_state.staff_zone_timers[track_id] = time.time()
                    else:
                        elapsed = time.time() - st.session_state.staff_zone_timers[track_id]
                        cv2.putText(frame, f"{int(elapsed)}s", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                        if elapsed >= STAFF_LIMIT:
                            st.session_state.staff_ids.add(track_id)
                            remove_false_visitor(track_id)
                            log_to_database(track_id, "Staf Aktif")
                            st.session_state.count_in = max(0, st.session_state.count_in - 1)
                            is_staff = True # Segera update status agar warnanya langsung berubah
                elif track_id in st.session_state.staff_zone_timers:
                    del st.session_state.staff_zone_timers[track_id]

                # --- BLOKIR STAF AGAR TIDAK TERHITUNG SEBAGAI PEMBELI/PENGUNJUNG ---
                if not is_staff:
                    # --- LOGIKA PEMBELI (Dinamis) ---
                    if cv2.pointPolygonTest(CASHIER_ZONE, (cx, cy), False) >= 0 and not is_buyer:
                        if track_id not in st.session_state.cashier_zone_timers:
                            st.session_state.cashier_zone_timers[track_id] = time.time()
                        else:
                            elapsed = time.time() - st.session_state.cashier_zone_timers[track_id]
                            cv2.putText(frame, f"Antre: {int(elapsed)}s", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
                            if elapsed >= BUYER_LIMIT:
                                st.session_state.buyer_ids.add(track_id)
                                st.session_state.count_buyer += 1
                                log_to_database(track_id, "Pembeli Baru")
                    elif track_id in st.session_state.cashier_zone_timers:
                        del st.session_state.cashier_zone_timers[track_id]

                    # --- LOGIKA MASUK/KELUAR GARIS PINTU ---
                    if track_id not in st.session_state.track_states:
                        st.session_state.track_states[track_id] = 'kiri' if cx < LINE_X else 'kanan'
                    else:
                        current_state = st.session_state.track_states[track_id]
                        if current_state == 'kiri' and cx > LINE_X + 40:
                            st.session_state.count_in += 1
                            st.session_state.track_states[track_id] = 'kanan'
                            log_to_database(track_id, "Masuk")
                        elif current_state == 'kanan' and cx < LINE_X - 40:
                            st.session_state.count_out += 1
                            st.session_state.track_states[track_id] = 'kiri'
                            log_to_database(track_id, "Keluar")

                # --- UBAH WARNA OTOMATIS BERDASARKAN STATUS ---
                # (Sekarang baris ini tidak akan dilewati lagi oleh Staf)
                color = (0, 165, 255) if is_buyer else ((255, 0, 0) if is_staff else (0, 255, 0))
                role_text = "STAFF" if is_staff else ("PEMBELI" if is_buyer else "PENGUNJUNG")
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"ID:{track_id} {role_text}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Update Metrics Real-time dengan teks dinamis
        val_in.metric("Total Masuk (Hari Ini)", st.session_state.count_in)
        val_buy.metric(f"Total Pembeli (Dwell > {BUYER_LIMIT}s)", st.session_state.count_buyer)
        rate = round((st.session_state.count_buyer / st.session_state.count_in * 100), 1) if st.session_state.count_in > 0 else 0
        val_rate.metric("Conversion Rate", f"{rate}%")

        FRAME_WINDOW.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_container_width=True)
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