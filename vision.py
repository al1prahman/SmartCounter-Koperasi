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
                
                # GUNAKAN TITIK KAKI UNTUK ZONA (Lebih Akurat)
                y_bawah = y2 
                
                # 1. DAFTARKAN PENGUNJUNG BARU KE DALAM MEMORI
                if track_id not in st.session_state.visitor_db:
                    st.session_state.visitor_db[track_id] = {
                        "status": "pengunjung",
                        "pos_h": 'kiri' if cx < LINE_POS else 'kanan', # Posisi Vertikal
                        "pos_v": 'atas' if cy < LINE_POS else 'bawah', # Posisi Horizontal
                        "waktu_staf": None,
                        "waktu_kasir": None,
                        "terhitung_masuk": False
                    }
                
                memori = st.session_state.visitor_db[track_id]
                is_staff = (memori["status"] == "staf")
                is_buyer = (memori["status"] == "pembeli")

                # 2. LOGIKA ZONA STAF (Waktu Tunggu Konversi)
                if not is_staff and not is_buyer:
                    if cv2.pointPolygonTest(STAFF_ZONE, (cx, y_bawah), False) >= 0:
                        if memori["waktu_staf"] is None:
                            memori["waktu_staf"] = time.time()
                        else:
                            elapsed = time.time() - memori["waktu_staf"]
                            if elapsed >= STAFF_LIMIT:
                                memori["status"] = "staf"
                                is_staff = True
                                log_to_database(track_id, "Staf Aktif")
                                add_log(track_id, "Staf Terdeteksi", "Zona Staf", f"{int(elapsed)}s")
                    else:
                        memori["waktu_staf"] = None # Reset jika keluar zona

                # 3. LOGIKA ZONA KASIR (Waktu Tunggu Konversi)
                if not is_staff and not is_buyer:
                    if cv2.pointPolygonTest(CASHIER_ZONE, (cx, y_bawah), False) >= 0:
                        if memori["waktu_kasir"] is None:
                            memori["waktu_kasir"] = time.time()
                        else:
                            elapsed = time.time() - memori["waktu_kasir"]
                            if elapsed >= BUYER_LIMIT:
                                memori["status"] = "pembeli"
                                is_buyer = True
                                st.session_state.count_buyer += 1
                                log_to_database(track_id, "Pembeli Baru")
                                add_log(track_id, "Pembeli Baru", "Kasir", f"{int(elapsed)}s")
                    else:
                        memori["waktu_kasir"] = None

                # 4. LOGIKA GARIS PINTU (Tanpa Jeda Pixel/Buffer)
                if LINE_ORIENT == "Vertikal":
                    pos_sekarang = 'kiri' if cx < LINE_POS else 'kanan'
                    if memori["pos_h"] == 'kiri' and pos_sekarang == 'kanan':
                        if ENTRY_DIR == "Kiri ke Kanan" and not memori["terhitung_masuk"]:
                            st.session_state.count_in += 1
                            memori["terhitung_masuk"] = True
                            log_to_database(track_id, "Masuk")
                            add_log(track_id, "Masuk", "Pintu")
                        elif ENTRY_DIR == "Kanan ke Kiri":
                            st.session_state.count_out += 1
                    
                    elif memori["pos_h"] == 'kanan' and pos_sekarang == 'kiri':
                        if ENTRY_DIR == "Kanan ke Kiri" and not memori["terhitung_masuk"]:
                            st.session_state.count_in += 1
                            memori["terhitung_masuk"] = True
                            log_to_database(track_id, "Masuk")
                            add_log(track_id, "Masuk", "Pintu")
                        elif ENTRY_DIR == "Kiri ke Kanan":
                            st.session_state.count_out += 1
                    memori["pos_h"] = pos_sekarang

                else: # Horizontal
                    pos_sekarang = 'atas' if cy < LINE_POS else 'bawah'
                    if memori["pos_v"] == 'atas' and pos_sekarang == 'bawah':
                        if ENTRY_DIR == "Atas ke Bawah" and not memori["terhitung_masuk"]:
                            st.session_state.count_in += 1
                            memori["terhitung_masuk"] = True
                            log_to_database(track_id, "Masuk")
                            add_log(track_id, "Masuk", "Pintu")
                        elif ENTRY_DIR == "Bawah ke Atas":
                            st.session_state.count_out += 1
                    
                    elif memori["pos_v"] == 'bawah' and pos_sekarang == 'atas':
                        if ENTRY_DIR == "Bawah ke Atas" and not memori["terhitung_masuk"]:
                            st.session_state.count_in += 1
                            memori["terhitung_masuk"] = True
                            log_to_database(track_id, "Masuk")
                            add_log(track_id, "Masuk", "Pintu")
                        elif ENTRY_DIR == "Atas ke Bawah":
                            st.session_state.count_out += 1
                    memori["pos_v"] = pos_sekarang

                # 5. PEWARNAAN KOTAK
                color = (53, 107, 255) if is_buyer else ((200, 100, 50) if is_staff else (167, 201, 0))
                label = "Pembeli" if is_buyer else ("Staf" if is_staff else "Pengunjung")
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.rectangle(frame, (x1, y1-20), (x1+80, y1), color, -1)
                cv2.putText(frame, f"#{track_id} {label}", (x1+5, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)