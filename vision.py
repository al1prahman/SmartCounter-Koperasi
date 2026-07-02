import cv2
import numpy as np
import time
from ultralytics import YOLO
import streamlit as st
from database import log_to_database, add_log
from ui_styles import render_log_table

@st.cache_resource
def load_model():
    return YOLO('best.pt')

def run_camera_loop(video_path, cfg, FRAME_WINDOW, LOG_WINDOW, update_metrics_ui):
    model = load_model()
    cap = cv2.VideoCapture(video_path)
    
    LINE_ORIENT = cfg["LINE_ORIENT"]
    LINE_POS = cfg["LINE_POS"]
    ENTRY_DIR = cfg["ENTRY_DIR"]
    STAFF_LIMIT = cfg["STAFF_LIMIT"]
    BUYER_LIMIT = cfg["BUYER_LIMIT"]
    
    # --- PENGATURAN BATAS PINTU ---
    # Sesuaikan angka Y ini agar pas dengan tinggi pintu di kamera Anda
    PINTU_Y_START = 150 
    PINTU_Y_END = 450
    
    STAFF_ZONE = np.array([[cfg["stf_x"], cfg["stf_y"]], [cfg["stf_x"]+cfg["stf_w"], cfg["stf_y"]], [cfg["stf_x"]+cfg["stf_w"], cfg["stf_y"]+cfg["stf_h"]], [cfg["stf_x"], cfg["stf_y"]+cfg["stf_h"]]], np.int32)
    CASHIER_ZONE = np.array([[cfg["ksr_x"], cfg["ksr_y"]], [cfg["ksr_x"]+cfg["ksr_w"], cfg["ksr_y"]], [cfg["ksr_x"]+cfg["ksr_w"], cfg["ksr_y"]+cfg["ksr_h"]], [cfg["ksr_x"], cfg["ksr_y"]+cfg["ksr_h"]]], np.int32)

    if isinstance(video_path, int):
        cap.set(3, 640); cap.set(4, 480)
        
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        frame_count += 1
        if frame_count % 2 == 0: continue
        
        # Resize Canvas
        h_asli, w_asli = frame.shape[:2]
        scale = min(640 / w_asli, 480 / h_asli)
        frame_resized = cv2.resize(frame, (int(w_asli * scale), int(h_asli * scale)))
        canvas = np.zeros((480, 640, 3), dtype=np.uint8)
        canvas[(480-frame_resized.shape[0])//2 : (480+frame_resized.shape[0])//2, 
               (640-frame_resized.shape[1])//2 : (640+frame_resized.shape[1])//2] = frame_resized
        frame = canvas

        # Drawing Garis & Zona
        if LINE_ORIENT == "Vertikal":
            cv2.line(frame, (LINE_POS, PINTU_Y_START), (LINE_POS, PINTU_Y_END), (30, 77, 140), 4)
        else:
            cv2.line(frame, (PINTU_Y_START, LINE_POS), (PINTU_Y_END, LINE_POS), (30, 77, 140), 4)

        cv2.polylines(frame, [STAFF_ZONE], True, (200, 100, 50), 2)
        cv2.putText(frame, "Zona Staf", (cfg["stf_x"], cfg["stf_y"] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 100, 50), 2)

        cv2.polylines(frame, [CASHIER_ZONE], True, (53, 107, 255), 2)
        cv2.putText(frame, "Zona Kasir", (cfg["ksr_x"], cfg["ksr_y"] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (53, 107, 255), 2)


        # TRACKING
        results = model.track(frame, persist=True, tracker="bytetrack.yaml", device='cpu', imgsz=320, verbose=False)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.int().cpu().numpy()

            for box, track_id in zip(boxes, ids):
                x1, y1, x2, y2 = map(int, box)
                cx, cy = (x1+x2)//2, (y1+y2)//2
                y_bawah = y2 

                if track_id not in st.session_state.visitor_db:
                    st.session_state.visitor_db[track_id] = {
                        "status": "pengunjung", "pos_h": 'kiri' if cx < LINE_POS else 'kanan',
                        "terhitung_masuk": False, "waktu_kasir": None, "waktu_staf": None
                    }
                
                memori = st.session_state.visitor_db[track_id]

                # LOGIKA ZONA STAF & KASIR
                if memori["status"] == "pengunjung":
                    if cv2.pointPolygonTest(STAFF_ZONE, (cx, y_bawah), False) >= 0:
                        memori["waktu_staf"] = (memori["waktu_staf"] or time.time())
                        if time.time() - memori["waktu_staf"] >= STAFF_LIMIT:
                            memori["status"] = "staf"
                            # Jika dia awalnya terhitung masuk sebagai pengunjung, kurangi angkanya
                            if memori["terhitung_masuk"]:
                                st.session_state.count_in -= 1 
                            add_log(track_id, "Staf Terdeteksi", "Zona Staf")
                    elif cv2.pointPolygonTest(CASHIER_ZONE, (cx, y_bawah), False) >= 0:
                        memori["waktu_kasir"] = (memori["waktu_kasir"] or time.time())
                        if time.time() - memori["waktu_kasir"] >= BUYER_LIMIT:
                            memori["status"] = "pembeli"
                            st.session_state.count_buyer += 1
                            log_to_database(track_id, "Pembeli Baru")
                            add_log(track_id, "Pembeli Baru", "Kasir")
                    else:
                        memori["waktu_kasir"] = None; memori["waktu_staf"] = None

                # LOGIKA GARIS PINTU (Terpotong)
                if PINTU_Y_START <= y_bawah <= PINTU_Y_END:
                    pos_sekarang = 'kiri' if cx < LINE_POS else 'kanan'
                    if memori["pos_h"] == 'kiri' and pos_sekarang == 'kanan' and ENTRY_DIR == "Kiri ke Kanan" and not memori["terhitung_masuk"]:
                        st.session_state.count_in += 1; memori["terhitung_masuk"] = True; log_to_database(track_id, "Masuk"); add_log(track_id, "Masuk", "Pintu")
                    elif memori["pos_h"] == 'kanan' and pos_sekarang == 'kiri' and ENTRY_DIR == "Kanan ke Kiri" and not memori["terhitung_masuk"]:
                        st.session_state.count_in += 1; memori["terhitung_masuk"] = True; log_to_database(track_id, "Masuk"); add_log(track_id, "Masuk", "Pintu")
                    memori["pos_h"] = pos_sekarang
                else:
                    # Update posisi horizontal jika di luar pintu agar memori arah jalan tidak tersangkut
                    memori["pos_h"] = 'kiri' if cx < LINE_POS else 'kanan'

                # PEWARNAAN BARU
                if memori["status"] == "staf":
                    color = (255, 0, 0) # Biru (OpenCV menggunakan format BGR)
                    label = "Staf"
                elif memori["status"] == "pembeli":
                    color = (0, 165, 255) # Oranye
                    label = "Pembeli"
                else:
                    color = (0, 255, 0) # Hijau
                    label = "Pengunjung"

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"ID:{track_id} {label}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # UPDATE UI
        if frame_count % 5 == 0:
            update_metrics_ui()
            LOG_WINDOW.markdown(render_log_table(), unsafe_allow_html=True)

        success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if success: FRAME_WINDOW.image(buffer.tobytes(), use_container_width=True)
    
    cap.release()