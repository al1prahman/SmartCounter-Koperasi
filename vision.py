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
    
    # Ambil Config
    LINE_ORIENT = cfg["LINE_ORIENT"]
    LINE_POS = cfg["LINE_POS"]
    ENTRY_DIR = cfg["ENTRY_DIR"]
    STAFF_LIMIT = cfg["STAFF_LIMIT"]
    BUYER_LIMIT = cfg["BUYER_LIMIT"]
    
    STAFF_ZONE = np.array([[cfg["stf_x"], cfg["stf_y"]], [cfg["stf_x"]+cfg["stf_w"], cfg["stf_y"]], [cfg["stf_x"]+cfg["stf_w"], cfg["stf_y"]+cfg["stf_h"]], [cfg["stf_x"], cfg["stf_y"]+cfg["stf_h"]]], np.int32)
    CASHIER_ZONE = np.array([[cfg["ksr_x"], cfg["ksr_y"]], [cfg["ksr_x"]+cfg["ksr_w"], cfg["ksr_y"]], [cfg["ksr_x"]+cfg["ksr_w"], cfg["ksr_y"]+cfg["ksr_h"]], [cfg["ksr_x"], cfg["ksr_y"]+cfg["ksr_h"]]], np.int32)

    # Set resolusi kamera live
    if isinstance(video_path, int):
        cap.set(3, 640); cap.set(4, 480)
        
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            st.success("✅ Pemutaran video selesai!")
            break
        
        frame_count += 1
        if frame_count % 2 == 0: continue
        
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

        if LINE_ORIENT == "Vertikal":
            cv2.line(frame, (LINE_POS, 0), (LINE_POS, 480), (30, 77, 140), 2)
        else:
            cv2.line(frame, (0, LINE_POS), (640, LINE_POS), (30, 77, 140), 2)

        cv2.polylines(frame, [STAFF_ZONE], True, (200, 100, 50), 2)
        cv2.putText(frame, "ZONA STAF", (STAFF_ZONE[0][0], STAFF_ZONE[0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 100, 50), 1)

        cv2.polylines(frame, [CASHIER_ZONE], True, (53, 107, 255), 2)
        cv2.putText(frame, "KASIR", (CASHIER_ZONE[0][0], CASHIER_ZONE[0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (53, 107, 255), 1)

        # Perbaikan variabel frame_kecil menjadi frame
        results = model.track(frame, persist=True, tracker="bytetrack.yaml", device="cpu", imgsz=480)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.int().cpu().numpy()

            for box, track_id in zip(boxes, ids):
                x1, y1, x2, y2 = map(int, box)
                cx, cy = (x1+x2)//2, (y1+y2)//2
                
                is_staff = track_id in st.session_state.staff_ids
                is_buyer = track_id in st.session_state.buyer_ids
                
                if cv2.pointPolygonTest(STAFF_ZONE, (cx, cy), False) >= 0 and not is_staff and not is_buyer:
                    if track_id not in st.session_state.staff_zone_timers:
                        st.session_state.staff_zone_timers[track_id] = time.time()
                    else:
                        elapsed = time.time() - st.session_state.staff_zone_timers[track_id]
                        if elapsed >= STAFF_LIMIT:
                            st.session_state.staff_ids.add(track_id)
                            log_to_database(track_id, "Staf Aktif")
                            add_log(track_id, "Staf Terdeteksi", "Zona Staf", f"{int(elapsed)}s")
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
                                add_log(track_id, "Pembeli Baru", "Kasir", f"{int(elapsed)}s")
                    elif track_id in st.session_state.cashier_zone_timers:
                        del st.session_state.cashier_zone_timers[track_id]

                    # Logika Penyeberangan Garis Masuk / Keluar
                    if LINE_ORIENT == "Vertikal":
                        if track_id not in st.session_state.track_states:
                            st.session_state.track_states[track_id] = 'kiri' if cx < LINE_POS else 'kanan'
                        else:
                            current_state = st.session_state.track_states[track_id]
                            if current_state == 'kiri' and cx > LINE_POS + 15:
                                if ENTRY_DIR == "Kiri ke Kanan":
                                    st.session_state.count_in += 1
                                    log_to_database(track_id, "Masuk")
                                    add_log(track_id, "Masuk", "Pintu Utama")
                                else:
                                    st.session_state.count_out += 1
                                    log_to_database(track_id, "Keluar")
                                    add_log(track_id, "Keluar", "Pintu Utama")
                                st.session_state.track_states[track_id] = 'kanan'
                            elif current_state == 'kanan' and cx < LINE_POS - 15:
                                if ENTRY_DIR == "Kiri ke Kanan":
                                    st.session_state.count_out += 1
                                    log_to_database(track_id, "Keluar")
                                    add_log(track_id, "Keluar", "Pintu Utama")
                                else:
                                    st.session_state.count_in += 1
                                    log_to_database(track_id, "Masuk")
                                    add_log(track_id, "Masuk", "Pintu Utama")
                                st.session_state.track_states[track_id] = 'kiri'
                    else: # Horizontal
                        if track_id not in st.session_state.track_states:
                            st.session_state.track_states[track_id] = 'atas' if cy < LINE_POS else 'bawah'
                        else:
                            current_state = st.session_state.track_states[track_id]
                            if current_state == 'atas' and cy > LINE_POS + 15:
                                if ENTRY_DIR == "Atas ke Bawah":
                                    st.session_state.count_in += 1
                                    log_to_database(track_id, "Masuk")
                                    add_log(track_id, "Masuk", "Pintu Utama")
                                else:
                                    st.session_state.count_out += 1
                                    log_to_database(track_id, "Keluar")
                                    add_log(track_id, "Keluar", "Pintu Utama")
                                st.session_state.track_states[track_id] = 'bawah'
                            elif current_state == 'bawah' and cy < LINE_POS - 15:
                                if ENTRY_DIR == "Atas ke Bawah":
                                    st.session_state.count_out += 1
                                    log_to_database(track_id, "Keluar")
                                    add_log(track_id, "Keluar", "Pintu Utama")
                                else:
                                    st.session_state.count_in += 1
                                    log_to_database(track_id, "Masuk")
                                    add_log(track_id, "Masuk", "Pintu Utama")
                                st.session_state.track_states[track_id] = 'atas'

                color = (53, 107, 255) if is_buyer else ((200, 100, 50) if is_staff else (167, 201, 0))
                label = "Pembeli" if is_buyer else ("Staf" if is_staff else "Pengunjung")
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
                cv2.rectangle(frame, (x1, y1-20), (x1+80, y1), color, -1)
                cv2.putText(frame, f"ID:{track_id} {label}", (x1+5, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,0,0), 1)

        if frame_count % 5 == 0 or frame_count == 1:
            update_metrics_ui()
            LOG_WINDOW.markdown(render_log_table(), unsafe_allow_html=True)

        FRAME_WINDOW.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_container_width=True)
    
    cap.release()