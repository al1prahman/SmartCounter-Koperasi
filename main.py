from ultralytics import YOLO
import cv2

model = YOLO('yolov8n.pt')
cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# --- KONFIGURASI GARIS & PENGHITUNG ---
LINE_X = 640  
OFFSET = 40  # Jarak toleransi (40 piksel ke kiri dan kanan garis)

count_in = 0
count_out = 0

# Menyimpan status posisi setiap orang ('kiri' atau 'kanan')
track_states = {}

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 1. Gambar Garis Utama dan Garis Toleransi
    cv2.line(frame, (LINE_X, 0), (LINE_X, frame.shape[0]), (0, 255, 255), 2)
    # Garis bayangan untuk batas aman (Opsional: bisa dihapus jika tampilan terlalu ramai)
    cv2.line(frame, (LINE_X - OFFSET, 0), (LINE_X - OFFSET, frame.shape[0]), (50, 50, 50), 1)
    cv2.line(frame, (LINE_X + OFFSET, 0), (LINE_X + OFFSET, frame.shape[0]), (50, 50, 50), 1)

    cv2.putText(frame, "Garis Batas", (LINE_X + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    # 2. Lacak Objek dengan Optimasi Performa (imgsz=320 sangat krusial untuk mencegah delay)
    results = model.track(frame, persist=True, classes=[0], verbose=False, imgsz=320)
    
    if results[0].boxes is not None and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()  
        track_ids = results[0].boxes.id.int().cpu().numpy()  

        for box, track_id in zip(boxes, track_ids):
            x1, y1, x2, y2 = map(int, box)
            
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"ID: {track_id}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # 4. Logika Perlintasan dengan Zona Toleransi (State Machine)
            if track_id not in track_states:
                # Daftarkan posisi awal pengunjung saat pertama kali terekam kamera
                track_states[track_id] = 'kiri' if cx < LINE_X else 'kanan'
            else:
                current_state = track_states[track_id]
                
                # Jika statusnya di kiri, dan dia melangkah melewati batas toleransi kanan = MASUK
                if current_state == 'kiri' and cx > (LINE_X + OFFSET):
                    count_out += 1
                    track_states[track_id] = 'kanan' # Perbarui status posisinya
                
                # Jika statusnya di kanan, dan dia melangkah melewati batas toleransi kiri = KELUAR
                elif current_state == 'kanan' and cx < (LINE_X - OFFSET):
                    count_in += 1
                    track_states[track_id] = 'kiri' # Perbarui status posisinya

    # 5. Tampilkan Teks Total
    cv2.putText(frame, f"Masuk: {count_in}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
    cv2.putText(frame, f"Keluar: {count_out}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    cv2.imshow("Smart Counter - Entrance Gate", frame)

    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()