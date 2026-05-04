from ultralytics import YOLO
import cv2
import numpy as np
import time

model = YOLO('yolov8n.pt')
cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# --- KONFIGURASI GARIS PINTU (STEP 7) ---
LINE_X = 640  
OFFSET = 40  
count_in = 0
count_out = 0
track_states = {}

# --- KONFIGURASI ZONA GEOFENCING (STEP 8 & 9) ---
# TENTUKAN KOORDINAT AREA (x, y) - Sesuaikan dengan posisi kamera Anda nanti!
# Format: [Kiri-Atas, Kanan-Atas, Kanan-Bawah, Kiri-Bawah]
STAFF_ZONE = np.array([[100, 100], [400, 100], [400, 400], [100, 400]], np.int32)
CASHIER_ZONE = np.array([[800, 200], [1200, 200], [1200, 600], [800, 600]], np.int32)

STAFF_TIME_LIMIT = 30  # 30 detik batas waktu untuk staf
BUYER_TIME_LIMIT = 20  # 20 detik batas waktu untuk konversi pembeli

staff_zone_timers = {}   # Mencatat kapan ID masuk area staf
cashier_zone_timers = {} # Mencatat kapan ID masuk area kasir

staff_ids = set() # Daftar ID yang sudah fix dilabeli Staf
buyer_ids = set() # Daftar ID yang sudah fix dilabeli Pembeli
count_buyer = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 1. Gambar Visual Area dan Garis di Layar
    cv2.line(frame, (LINE_X, 0), (LINE_X, frame.shape[0]), (0, 255, 255), 2)
    
    # Gambar Zona Staf (Warna Biru)
    cv2.polylines(frame, [STAFF_ZONE], isClosed=True, color=(255, 0, 0), thickness=2)
    cv2.putText(frame, "ZONA STAF", (STAFF_ZONE[0][0], STAFF_ZONE[0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    
    # Gambar Zona Kasir (Warna Oranye)
    cv2.polylines(frame, [CASHIER_ZONE], isClosed=True, color=(0, 165, 255), thickness=2)
    cv2.putText(frame, "ZONA KASIR", (CASHIER_ZONE[0][0], CASHIER_ZONE[0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

    # 2. Lacak Objek AI
    results = model.track(frame, persist=True, classes=[0], verbose=False, imgsz=320)
    
    if results[0].boxes is not None and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()  
        track_ids = results[0].boxes.id.int().cpu().numpy()  

        for box, track_id in zip(boxes, track_ids):
            x1, y1, x2, y2 = map(int, box)
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            
            # Cek identitas ID ini (Apakah Staf, Pembeli, atau sekadar Pengunjung?)
            is_staff = track_id in staff_ids
            is_buyer = track_id in buyer_ids

            # Beri warna Bounding Box sesuai Identitas: Staf=Biru, Pembeli=Oranye, Pengunjung=Hijau
            box_color = (255, 0, 0) if is_staff else ((0, 165, 255) if is_buyer else (0, 255, 0))
            role_text = "STAFF" if is_staff else ("PEMBELI" if is_buyer else "PENGUNJUNG")

            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            cv2.putText(frame, f"ID:{track_id} {role_text}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

            # --- STEP 8: LOGIKA STAFF FILTERING ---
            # Cek apakah titik tengah pengunjung berada di dalam poligon Zona Staf
            in_staff_zone = cv2.pointPolygonTest(STAFF_ZONE, (cx, cy), False) >= 0
            
            if in_staff_zone and not is_staff:
                if track_id not in staff_zone_timers:
                    staff_zone_timers[track_id] = time.time() # Mulai stopwatch!
                else:
                    elapsed = time.time() - staff_zone_timers[track_id]
                    # Tampilkan teks timer berjalan
                    cv2.putText(frame, f"{int(elapsed)}s", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    
                    if elapsed >= STAFF_TIME_LIMIT:
                        staff_ids.add(track_id) # Kunci sebagai staf
            elif not in_staff_zone:
                # Jika dia keluar dari zona sebelum 30 detik, hapus/reset timernya
                if track_id in staff_zone_timers:
                    del staff_zone_timers[track_id]

            # JIKA DIA STAF, lewati logika penghitungan pembeli dan penghitungan pintu di bawah ini
            if is_staff:
                continue

            # --- STEP 9: LOGIKA ESTIMASI PEMBELI (CASHIER ROI) ---
            in_cashier_zone = cv2.pointPolygonTest(CASHIER_ZONE, (cx, cy), False) >= 0
            
            if in_cashier_zone and not is_buyer:
                if track_id not in cashier_zone_timers:
                    cashier_zone_timers[track_id] = time.time() # Mulai stopwatch!
                else:
                    elapsed = time.time() - cashier_zone_timers[track_id]
                    # Tampilkan teks timer berjalan
                    cv2.putText(frame, f"Antre: {int(elapsed)}s", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
                    
                    if elapsed >= BUYER_TIME_LIMIT:
                        buyer_ids.add(track_id) # Kunci sebagai pembeli
                        count_buyer += 1 # Tambah angka metrik pembeli
            elif not in_cashier_zone:
                # Harus berturut-turut! Jika keluar barisan, timer di-reset.
                if track_id in cashier_zone_timers:
                    del cashier_zone_timers[track_id]

            # --- KEMBALI KE STEP 7: LOGIKA GARIS PINTU ---
            if track_id not in track_states:
                track_states[track_id] = 'kiri' if cx < LINE_X else 'kanan'
            else:
                current_state = track_states[track_id]
                if current_state == 'kiri' and cx > (LINE_X + OFFSET):
                    count_in += 1
                    track_states[track_id] = 'kanan'
                elif current_state == 'kanan' and cx < (LINE_X - OFFSET):
                    count_out += 1
                    track_states[track_id] = 'kiri'

    # Tampilkan Teks Total Keseluruhan
    cv2.putText(frame, f"Masuk: {count_in}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
    cv2.putText(frame, f"Keluar: {count_out}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    cv2.putText(frame, f"Total Pembeli: {count_buyer}", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 3)

    cv2.imshow("Smart Counter", frame)

    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()