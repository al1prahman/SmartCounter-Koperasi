import streamlit as st
from ultralytics import YOLO
import cv2
import numpy as np
import time
import mysql.connector
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="KMP Smart Monitor", layout="wide", initial_sidebar_state="expanded")

# --- INJEKSI CSS UNTUK DESAIN DARK THEME SaaS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Mengembalikan tombol sidebar dan menyembunyikan elemen tak perlu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;}
    
    /* Top Navbar Custom */
    .top-nav {
        display: flex; justify-content: space-between; align-items: center;
        background-color: #0A1628; padding: 10px 20px; border-bottom: 1px solid #1E4D8C;
        margin-top: -60px; margin-bottom: 20px; color: white; font-weight: 600;
    }
    .status-live { color: #00C9A7; display: flex; align-items: center; font-size: 14px;}
    .status-live span { height: 10px; width: 10px; background-color: #00C9A7; border-radius: 50%; display: inline-block; margin-right: 8px; box-shadow: 0 0 8px #00C9A7;}
    
    /* Styling Kartu Metrik */
    .metric-card {
        background-color: #0F2040; border-left: 4px solid #1E4D8C;
        border-radius: 12px; padding: 16px; margin-bottom: 20px;
    }
    .metric-title { color: #A0AEC0; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
    .metric-value { font-size: 36px; font-weight: 700; margin-bottom: 5px; }
    .val-white { color: #FFFFFF; }
    .val-teal { color: #00C9A7; }
    .val-orange { color: #FF6B35; }
    .metric-sub { color: #718096; font-size: 12px; }
    
    /* Styling Tabel Activity Log */
    .log-table { width: 100%; border-collapse: collapse; font-size: 13px; color: #A0AEC0;}
    .log-table th { text-align: left; padding: 12px 8px; border-bottom: 1px solid #1E4D8C; color: white;}
    .log-table td { padding: 10px 8px; border-bottom: 1px solid #0A1628;}
    .log-table tr:nth-child(even) { background-color: #0A1628; }
    .log-table tr:nth-child(odd) { background-color: #0F2040; }
    .badge-entry { background-color: rgba(0, 201, 167, 0.2); color: #00C9A7; padding: 4px 8px; border-radius: 4px; font-size: 11px;}
    .badge-buyer { background-color: rgba(255, 107, 53, 0.2); color: #FF6B35; padding: 4px 8px; border-radius: 4px; font-size: 11px;}
    .badge-staff { background-color: rgba(30, 77, 140, 0.4); color: #82B1FF; padding: 4px 8px; border-radius: 4px; font-size: 11px;}
    </style>
""", unsafe_allow_html=True)

# --- HEADER CUSTOM ---
st.markdown("""
<div class="top-nav">
    <div style="font-size: 18px; letter-spacing: 0.5px;">KMP Smart Monitor</div>
    <div style="display: flex; gap: 20px; align-items: center; color: #A0AEC0; font-weight: 400; font-size: 14px;">
        <div class="status-live"><span></span> LIVE</div>
    </div>
</div>
""", unsafe_allow_html=True)

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

# Activity Log UI Helper
def add_log(track_id, event, zone, duration="-"):
    time_str = datetime.now().strftime("%H:%M:%S")
    st.session_state.recent_logs.insert(0, {"time": time_str, "id": f"#{track_id:04d}", "event": event, "zone": zone, "duration": duration})
    if len(st.session_state.recent_logs) > 6: st.session_state.recent_logs.pop()

def render_log_table():
    html = '<table class="log-table"><tr><th>Time</th><th>ID</th><th>Event</th><th>Zone</th><th>Duration</th></tr>'
    for log in st.session_state.recent_logs:
        badge_class = "badge-entry" if log['event'] == "Entry" else ("badge-buyer" if log['event'] == "Buyer Confirmed" else "badge-staff")
        html += f"<tr><td>{log['time']}</td><td>{log['id']}</td><td><span class='{badge_class}'>{log['event']}</span></td><td>{log['zone']}</td><td>{log['duration']}</td></tr>"
    html += '</table>'
    return html

if 'initialized' not in st.session_state:
    tin, tout, tbuy = fetch_today_stats()
    st.session_state.update({
        'initialized': True,
        'count_in': tin, 'count_out': tout, 'count_buyer': tbuy,
        'track_states': {}, 'staff_zone_timers': {}, 'cashier_zone_timers': {},
        'staff_ids': set(), 'buyer_ids': set(), 'recent_logs': []
    })

# --- UI METRIK ---
col1, col2, col3, col4 = st.columns(4)
ph_in = col1.empty()
ph_buy = col2.empty()
ph_rate = col3.empty()
ph_occ = col4.empty()

def update_metrics_ui():
    c_in = st.session_state.count_in
    c_buy = st.session_state.count_buyer
    c_out = st.session_state.count_out
    rate = round((c_buy / c_in * 100), 1) if c_in > 0 else 0
    occ = max(0, c_in - c_out)
    
    ph_in.markdown(f'<div class="metric-card"><div class="metric-title">TOTAL ENTRANCES TODAY</div><div class="metric-value val-white">{c_in}</div><div class="metric-sub">Updated live</div></div>', unsafe_allow_html=True)
    ph_buy.markdown(f'<div class="metric-card"><div class="metric-title">TOTAL BUYERS</div><div class="metric-value val-teal">{c_buy}</div><div class="metric-sub">Dwell time confirmed</div></div>', unsafe_allow_html=True)
    ph_rate.markdown(f'<div class="metric-card"><div class="metric-title">CONVERSION RATE</div><div class="metric-value val-orange">{rate}%</div><div class="metric-sub">Visitors → Buyers</div></div>', unsafe_allow_html=True)
    ph_occ.markdown(f'<div class="metric-card"><div class="metric-title">CURRENT OCCUPANCY</div><div class="metric-value val-white">{occ}</div><div class="metric-sub">Inside store now</div></div>', unsafe_allow_html=True)

update_metrics_ui()

# --- AREA GRAFIK & LOG (TATA LETAK BARU) ---
df_h, df_d = get_chart_data()
col_left, col_right = st.columns([6, 4])

with col_left:
    st.markdown('<div style="color:white; font-weight:600; margin-bottom:10px;">Hourly Traffic Today</div>', unsafe_allow_html=True)
    if not df_h.empty:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df_h['jam'].astype(str) + ':00', y=df_h['total'], mode='lines', name='Visitors', line=dict(color='#00C9A7', width=3, shape='spline'), fill='tozeroy', fillcolor='rgba(0, 201, 167, 0.1)'))
        fig1.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#A0AEC0', margin=dict(l=0, r=0, t=10, b=0))
        fig1.update_xaxes(showgrid=False, linecolor='#1E4D8C')
        fig1.update_yaxes(showgrid=True, gridcolor='#1E4D8C', gridwidth=1, griddash='dash')
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Belum ada data jam ini.")

    st.markdown('<div style="color:white; font-weight:600; margin-top:15px; margin-bottom:10px;">Recent Activity Log</div>', unsafe_allow_html=True)
    LOG_WINDOW = st.empty()

with col_right:
    st.markdown('<div style="color:white; font-weight:600; margin-bottom:10px;">7-Day Visitor vs Buyer</div>', unsafe_allow_html=True)
    if not df_d.empty:
        fig2 = go.Figure(data=[
            go.Bar(name='Visitors', x=df_d['tanggal'], y=df_d['Pengunjung'], marker_color='#00C9A7', marker_line_width=0),
            go.Bar(name='Buyers', x=df_d['tanggal'], y=df_d['Pembeli'], marker_color='#FF6B35', marker_line_width=0)
        ])
        fig2.update_layout(height=560, barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#A0AEC0', margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
        fig2.update_xaxes(showgrid=False, linecolor='#1E4D8C')
        fig2.update_yaxes(showgrid=True, gridcolor='#1E4D8C', griddash='dash')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Data historis tidak ditemukan.")

# --- AREA VIDEO (FULL WIDTH DI BAWAH) ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div style="color:white; font-weight:600; font-size:16px; margin-bottom:10px;">📹 Live Feed Active — YOLOv8n (Full View)</div>', unsafe_allow_html=True)
FRAME_WINDOW = st.empty()

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown('<div style="color:white; font-size:18px; font-weight:600; margin-bottom:20px;">Admin Panel<br><span style="color:#A0AEC0; font-size:12px; font-weight:400;">Operational View</span></div>', unsafe_allow_html=True)
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

st.sidebar.markdown("---")

# === PENGATURAN GARIS PINTU ===
st.sidebar.subheader("🚪 Pengaturan Garis Pintu")
LINE_ORIENT = st.sidebar.selectbox("Orientasi Garis Pintu", ["Vertikal", "Horizontal"])

if LINE_ORIENT == "Vertikal":
    LINE_POS = st.sidebar.slider("Posisi Koordinat (X)", 0, 640, 320)
    ENTRY_DIR = st.sidebar.radio("Definisi Arah 'Masuk':", ["Kiri ke Kanan", "Kanan ke Kiri"])
else:
    LINE_POS = st.sidebar.slider("Posisi Koordinat (Y)", 0, 480, 240)
    ENTRY_DIR = st.sidebar.radio("Definisi Arah 'Masuk':", ["Atas ke Bawah", "Bawah ke Atas"])

# === KONFIGURASI ZONA & WAKTU ===
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
    return YOLO('yolov8n.pt')
model = load_model()

# --- LOOP UTAMA KAMERA ---
if run_camera and video_path is not None:
    cap = cv2.VideoCapture(video_path)
    if video_source == "Kamera Live":
        cap.set(3, 640); cap.set(4, 480)
        
    frame_count = 0
    
    while run_camera:
        ret, frame = cap.read()
        if not ret:
            st.success("✅ Pemutaran video selesai!")
            break
        
        frame_count += 1
        
        # Letterbox 
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

        # Gambarkan Garis Pintu
        if LINE_ORIENT == "Vertikal":
            cv2.line(frame, (LINE_POS, 0), (LINE_POS, 480), (30, 77, 140), 2)
        else:
            cv2.line(frame, (0, LINE_POS), (640, LINE_POS), (30, 77, 140), 2)

        # Gambarkan Area Poligon Zona
        cv2.polylines(frame, [STAFF_ZONE], True, (200, 100, 50), 2)
        cv2.putText(frame, "STAFF ZONE", (STAFF_ZONE[0][0], STAFF_ZONE[0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 100, 50), 1)

        cv2.polylines(frame, [CASHIER_ZONE], True, (53, 107, 255), 2)
        cv2.putText(frame, "CASHIER ZONE", (CASHIER_ZONE[0][0], CASHIER_ZONE[0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (53, 107, 255), 1)

        results = model.track(frame, persist=True, classes=[0], verbose=False, conf=0.25, tracker="bytetrack.yaml")
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.int().cpu().numpy()

            for box, track_id in zip(boxes, ids):
                x1, y1, x2, y2 = map(int, box)
                cx, cy = (x1+x2)//2, (y1+y2)//2
                
                is_staff = track_id in st.session_state.staff_ids
                is_buyer = track_id in st.session_state.buyer_ids
                
                if cv2.pointPolygonTest(STAFF_ZONE, (cx, cy), False) >= 0 and not is_staff:
                    if track_id not in st.session_state.staff_zone_timers:
                        st.session_state.staff_zone_timers[track_id] = time.time()
                    else:
                        elapsed = time.time() - st.session_state.staff_zone_timers[track_id]
                        if elapsed >= STAFF_LIMIT:
                            st.session_state.staff_ids.add(track_id)
                            remove_false_visitor(track_id)
                            log_to_database(track_id, "Staf Aktif")
                            add_log(track_id, "Staff Detected", "Staff Zone", f"{int(elapsed)}s")
                            st.session_state.count_in = max(0, st.session_state.count_in - 1)
                            is_staff = True
                elif track_id in st.session_state.staff_zone_timers:
                    del st.session_state.staff_zone_timers[track_id]

                if not is_staff:
                    if cv2.pointPolygonTest(CASHIER_ZONE, (cx, cy), False) >= 0 and not is_buyer:
                        if track_id not in st.session_state.cashier_zone_timers:
                            st.session_state.cashier_zone_timers[track_id] = time.time()
                        else:
                            elapsed = time.time() - st.session_state.cashier_zone_timers[track_id]
                            if elapsed >= BUYER_LIMIT:
                                st.session_state.buyer_ids.add(track_id)
                                st.session_state.count_buyer += 1
                                log_to_database(track_id, "Pembeli Baru")
                                add_log(track_id, "Buyer Confirmed", "Checkout", f"{int(elapsed)}s")
                    elif track_id in st.session_state.cashier_zone_timers:
                        del st.session_state.cashier_zone_timers[track_id]

                    if LINE_ORIENT == "Vertikal":
                        if track_id not in st.session_state.track_states:
                            st.session_state.track_states[track_id] = 'kiri' if cx < LINE_POS else 'kanan'
                        else:
                            current_state = st.session_state.track_states[track_id]
                            
                            if current_state == 'kiri' and cx > LINE_POS + 15:
                                if ENTRY_DIR == "Kiri ke Kanan":
                                    st.session_state.count_in += 1
                                    log_to_database(track_id, "Masuk")
                                    add_log(track_id, "Entry", "Main Door")
                                else:
                                    st.session_state.count_out += 1
                                    log_to_database(track_id, "Keluar")
                                    add_log(track_id, "Exit", "Main Door")
                                st.session_state.track_states[track_id] = 'kanan'
                                
                            elif current_state == 'kanan' and cx < LINE_POS - 15:
                                if ENTRY_DIR == "Kiri ke Kanan":
                                    st.session_state.count_out += 1
                                    log_to_database(track_id, "Keluar")
                                    add_log(track_id, "Exit", "Main Door")
                                else:
                                    st.session_state.count_in += 1
                                    log_to_database(track_id, "Masuk")
                                    add_log(track_id, "Entry", "Main Door")
                                st.session_state.track_states[track_id] = 'kiri'
                    else:
                        if track_id not in st.session_state.track_states:
                            st.session_state.track_states[track_id] = 'atas' if cy < LINE_POS else 'bawah'
                        else:
                            current_state = st.session_state.track_states[track_id]
                            
                            if current_state == 'atas' and cy > LINE_POS + 15:
                                if ENTRY_DIR == "Atas ke Bawah":
                                    st.session_state.count_in += 1
                                    log_to_database(track_id, "Masuk")
                                    add_log(track_id, "Entry", "Main Door")
                                else:
                                    st.session_state.count_out += 1
                                    log_to_database(track_id, "Keluar")
                                    add_log(track_id, "Exit", "Main Door")
                                st.session_state.track_states[track_id] = 'bawah'
                                
                            elif current_state == 'bawah' and cy < LINE_POS - 15:
                                if ENTRY_DIR == "Atas ke Bawah":
                                    st.session_state.count_out += 1
                                    log_to_database(track_id, "Keluar")
                                    add_log(track_id, "Exit", "Main Door")
                                else:
                                    st.session_state.count_in += 1
                                    log_to_database(track_id, "Masuk")
                                    add_log(track_id, "Entry", "Main Door")
                                st.session_state.track_states[track_id] = 'atas'

                # Flat UI Bounding Boxes
                color = (53, 107, 255) if is_buyer else ((200, 100, 50) if is_staff else (167, 201, 0))
                label = "Buyer" if is_buyer else ("Staff" if is_staff else "Visitor")
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
                cv2.rectangle(frame, (x1, y1-20), (x1+80, y1), color, -1)
                cv2.putText(frame, f"ID:{track_id} {label}", (x1+5, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,0,0), 1)

        if frame_count % 5 == 0 or frame_count == 1:
            update_metrics_ui()
            LOG_WINDOW.markdown(render_log_table(), unsafe_allow_html=True)

        FRAME_WINDOW.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_container_width=True)
    cap.release()
else:
    LOG_WINDOW.markdown(render_log_table(), unsafe_allow_html=True)