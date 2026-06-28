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

        # Drawing
        cv2.line(frame, (LINE_POS, 0), (LINE_POS, 480), (30, 77, 140), 2) if LINE_ORIENT == "Vertikal" else cv2.line(frame, (0, LINE_POS), (640, LINE_POS), (30, 77, 140), 2)
        cv2.polylines(frame, [STAFF_ZONE], True, (200, 100, 50), 2)
        cv2.polylines(frame, [CASHIER_ZONE], True, (53, 107, 255), 2)

        # TRACKING DENGAN CPU
        results = model.track(frame, persist=True, tracker="bytetrack.yaml", device='cpu', imgsz=320, verbose=False)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.int().cpu().numpy()

            for box, track_id in zip(boxes, ids):
                x1, y1, x2, y2 = map(int, box)
                cx, cy = (x1+x2)//2, (y1+y2)//2
                
                if track_id not in st.session_state.visitor_db:
                    st.session_state.visitor_db[track_id] = {"status": "pengunjung", "pos_h": 'kiri' if cx < LINE_POS else 'kanan', "pos_v": 'atas' if cy < LINE_POS else 'bawah', "waktu_staf": None, "waktu_kasir": None, "terhitung_masuk": False}
                
                memori = st.session_state.visitor_db[track_id]
                
                # Logic Zone & Line (gunakan logika yang sudah kita buat sebelumnya)
                # ... [Tempel logika zona dan garis yang sudah Anda tulis di sini] ...

                # Pewarnaan Kotak
                color = (53, 107, 255) if memori["status"] == "pembeli" else ((200, 100, 50) if memori["status"] == "staf" else (167, 201, 0))
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"#{track_id} {memori['status']}", (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

        # UPDATE UI DENGAN KOMPRESI JPEG
        if frame_count % 5 == 0:
            update_metrics_ui()
            LOG_WINDOW.markdown(render_log_table(), unsafe_allow_html=True)

        success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if success:
            FRAME_WINDOW.image(buffer.tobytes(), use_container_width=True)
    
    cap.release()