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

if 'initialized' not in st.session_state:
    tin, tout, tbuy = fetch_today_stats()
    st.session_state.update({
        'initialized': True,
        'count_in': tin, 'count_out': tout, 'count_buyer': tbuy,
        'track_states': {}, 'staff_zone_timers': {}, 'cashier_zone_timers': {},
        'staff_ids': set(), 'buyer_ids': set()
    })

# --- UI METRIK ---
c1, c2, c3 = st.columns(3)
val_in = c1.empty()
val_buy = c2.empty()
val_rate = c3.empty()

# Tampilkan metrik awal sebelum kamera berjalan
rate_awal = round((st.session_state.count_buyer / st.session_state.count_in * 100), 1) if st.session_state.count_in > 0 else 0
val_in.metric("Total Masuk (Hari Ini)", st.session_state.count_in)
val_buy.metric("Total Pembeli", st.session_state.count_buyer)
val_rate.metric("Conversion Rate", f"{rate_awal}%")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Kontrol Sistem")
video_source = st.sidebar.radio("📽️ Pilih Sumber Video:", ["Kamera Live", "Upload Video (MP4)"])

video_path = None
if video_source == "Kamera Live":
    cam_index = st.sidebar.number_input("Pilih ID Kamera", min_value=0, max_value=5, value=0)
    video_path = cam_index
else:
    uploaded_file = st.sidebar.file_uploader("Upload File Video Rekaman", type=['mp4', 'avi', 'mov'])
    if uploaded_file is not None:
        with open("temp_video.mp4", "wb") as f:
            f.write(uploaded_file.read())
        video_path = "temp_video.mp4"

run_camera = st.sidebar.checkbox("▶️ Jalankan Sistem AI", value=False)
show_charts = st.sidebar.checkbox("📈 Tampilkan Grafik Analitik", value=True)

st.sidebar.markdown("---")

# === PENGATURAN GARIS PINTU (Ditampilkan di luar agar langsung terlihat) ===
st.sidebar.subheader("🚪 Pengaturan Garis Pintu")
LINE_ORIENT = st.sidebar.selectbox("Orientasi Garis Pintu", ["Vertikal", "Horizontal"])

if LINE_ORIENT == "Vertikal":
    LINE_POS = st.sidebar.slider("Posisi Koordinat (X)", 0, 640, 320)
    ENTRY_DIR = st.sidebar.radio("Definisi Arah 'Masuk':", ["Kiri ke Kanan", "Kanan ke Kiri"])
else:
    LINE_POS = st.sidebar.slider("Posisi Koordinat (Y)", 0, 480, 240)
    ENTRY_DIR = st.sidebar.radio("Definisi Arah 'Masuk':", ["Atas ke Bawah", "Bawah ke Atas"])

# === KONFIGURASI ZONA & WAKTU (Disimpan dalam expander) ===
with st.sidebar.expander("🔲 Konfigurasi Zona & Waktu Tunggu", expanded=False):
    st.markdown("**Durasi Konversi (Detik)**")
    STAFF_LIMIT = st.slider("Waktu Tunggu Staf", 1, 60, 10) 
    BUYER_LIMIT = st.slider("Waktu Tunggu Pembeli", 1, 60, 10) 

    st.markdown("---")
    st.markdown("**Zona Staf (Biru)**")
    stf_x = st.slider("Staf: Posisi X", 0, 640, 50)
    stf_y = st.slider("Staf: Posisi Y", 0, 480, 50)
    stf_w = st.slider("Staf: Lebar", 50, 640, 200)
    stf_h = st.slider("Staf: Tinggi", 50, 480, 300)
    STAFF_ZONE = np.array([[stf_x, stf_y], [stf_x+stf_w, stf_y], [stf_x+stf_w, stf_y+stf_h], [stf_x, stf_y+stf_h]], np.int32)
    
    st.markdown("**Zona Kasir (Oranye)**")
    ksr_x = st.slider("Kasir: Posisi X", 0, 640, 380)
    ksr_y = st.slider("Kasir: Posisi Y", 0, 480, 50)
    ksr_w = st.slider("Kasir: Lebar", 50, 640, 200)
    ksr_h = st.slider("Kasir: Tinggi", 50, 480, 300)
    CASHIER_ZONE = np.array([[ksr_x, ksr_y], [ksr_x+ksr_w, ksr_y], [ksr_x+ksr_w, ksr_y+ksr_h], [ksr_x, ksr_y+ksr_h]], np.int32)

@st.cache_resource
def load_model():
    return YOLO('yolov8n.pt') # Gunakan YOLOv8n untuk stabilitas tracking
model = load_model()

st.write("### 🎥 Live / Recorded Camera Stream")
_, col_vid, _ = st.columns([1, 4, 1])
FRAME_WINDOW = col_vid.empty()

# --- LOOP UTAMA KAMERA ---
if run_camera and video_path is not None:
    cap = cv2.VideoCapture(video_path)
    if video_source == "Kamera Live":
        cap.set(3, 640); cap.set(4, 480)
        
    frame_count = 0 # Mengontrol jalur data UI agar FPS tinggi
    
    while run_camera:
        ret, frame = cap.read()
        if not ret:
            st.success("✅ Pemutaran video selesai!")
            break
        
        frame_count += 1
        
        # --- TEKNIK LETTERBOX (Mencegah Video iPhone Gepeng) ---
        h_asli, w_asli = frame.shape[:2]
        target_w, target_h = 640, 480
        scale = min(target_w / w_asli, target_h / h_asli)
        new_w, new_h = int(w_asli * scale), int(h_asli * scale)
        frame_resized = cv2.resize(frame, (new_w, new_h))
        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        x_offset = (target_w - new_w) // 2
        y_offset = (target_h - new_h) // 2
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = frame_resized
        frame = canvas

        # Gambarkan Garis Pintu Sesuai Orientasi Pilihan
        if LINE_ORIENT == "Vertikal":
            cv2.line(frame, (LINE_POS, 0), (LINE_POS, 480), (0, 255, 255), 2)
        else:
            cv2.line(frame, (0, LINE_POS), (640, LINE_POS), (0, 255, 255), 2)

        # Gambarkan Area Poligon Zona
        cv2.polylines(frame, [STAFF_ZONE], True, (255, 0, 0), 2)
        cv2.polylines(frame, [CASHIER_ZONE], True, (0, 165, 255), 2)

        # --- OPTIMASI FPS: Kembalikan imgsz=320 khusus YOLO ---
        results = model.track(frame, persist=True, classes=[0], verbose=False, conf=0.4, imgsz=320)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.int().cpu().numpy()

            for box, track_id in zip(boxes, ids):
                x1, y1, x2, y2 = map(int, box)
                cx, cy = (x1+x2)//2, (y1+y2)//2
                
                is_staff = track_id in st.session_state.staff_ids
                is_buyer = track_id in st.session_state.buyer_ids
                
                # Logika Penghitungan Waktu Staf
                if cv2.pointPolygonTest(STAFF_ZONE, (cx, cy), False) >= 0 and not is_staff:
                    if track_id not in st.session_state.staff_zone_timers:
                        st.session_state.staff_zone_timers[track_id] = time.time()
                    else:
                        elapsed = time.time() - st.session_state.staff_zone_timers[track_id]
                        cv2.putText(frame, f"Staf: {int(elapsed)}s", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                        if elapsed >= STAFF_LIMIT:
                            st.session_state.staff_ids.add(track_id)
                            remove_false_visitor(track_id)
                            log_to_database(track_id, "Staf Aktif")
                            st.session_state.count_in = max(0, st.session_state.count_in - 1)
                            is_staff = True
                elif track_id in st.session_state.staff_zone_timers:
                    del st.session_state.staff_zone_timers[track_id]

                if not is_staff:
                    # Logika Penghitungan Waktu Antrean Pembeli
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

                    # --- LOGIKA CROSSING DINAMIS (VERTIKAL VS HORIZONTAL) ---
                    if LINE_ORIENT == "Vertikal":
                        if track_id not in st.session_state.track_states:
                            st.session_state.track_states[track_id] = 'kiri' if cx < LINE_POS else 'kanan'
                        else:
                            current_state = st.session_state.track_states[track_id]
                            if current_state == 'kiri' and cx > LINE_POS + 30:
                                st.session_state.count_in += 1
                                st.session_state.track_states[track_id] = 'kanan'
                                log_to_database(track_id, "Masuk")
                            elif current_state == 'kanan' and cx < LINE_POS - 30:
                                st.session_state.count_out += 1
                                st.session_state.track_states[track_id] = 'kiri'
                                log_to_database(track_id, "Keluar")
                    else:
                        # Jika Horizontal, gunakan parameter sumbu 'cy' (Atas vs Bawah)
                        if track_id not in st.session_state.track_states:
                            st.session_state.track_states[track_id] = 'atas' if cy < LINE_POS else 'bawah'
                        else:
                            current_state = st.session_state.track_states[track_id]
                            if current_state == 'atas' and cy > LINE_POS + 30:
                                st.session_state.count_in += 1
                                st.session_state.track_states[track_id] = 'bawah'
                                log_to_database(track_id, "Masuk")
                            elif current_state == 'bawah' and cy < LINE_POS - 30:
                                st.session_state.count_out += 1
                                st.session_state.track_states[track_id] = 'atas'
                                log_to_database(track_id, "Keluar")

                # Penandaan Box Warna
                color = (0, 165, 255) if is_buyer else ((255, 0, 0) if is_staff else (0, 255, 0))
                role_text = "STAFF" if is_staff else ("PEMBELI" if is_buyer else "PENGUNJUNG")
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"ID:{track_id} {role_text}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # --- OPTIMASI WEBSOCKET: Update Angka UI Setiap 5 Frame Sekali ---
        if frame_count % 5 == 0 or frame_count == 1:
            val_in.metric("Total Masuk (Hari Ini)", st.session_state.count_in)
            val_buy.metric(f"Total Pembeli (Dwell > {BUYER_LIMIT}s)", st.session_state.count_buyer)
            rate = round((st.session_state.count_buyer / st.session_state.count_in * 100), 1) if st.session_state.count_in > 0 else 0
            val_rate.metric("Conversion Rate", f"{rate}%")

        # Render matriks gambar ke Web Dashboard
        FRAME_WINDOW.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_container_width=True)
    cap.release()

# --- AREA GRAFIK ---
if show_charts:
    st.write("---")
    st.write("### 📈 Analitik Kunjungan")
    df_h, df_d = get_chart_data()
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Trafik Pengunjung per Jam (Hari Ini)**")
        if not df_h.empty: st.line_chart(df_h.set_index('jam'))
        else: st.info("Belum ada data jam ini.")
    with col_b:
        st.write("**Pengunjung vs Pembeli (7 Hari Terakhir)**")
        if not df_d.empty: st.bar_chart(df_d.set_index('tanggal'))
        else: st.info("Data historis tidak ditemukan.")