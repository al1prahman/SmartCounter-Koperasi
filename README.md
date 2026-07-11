# 🛒 Smart Counter & Dwell Time Analysis - Koperasi Merah Putih

## 📖 Deskripsi Singkat
**Sistem Smart Counter dan Analisis Dwell Time** adalah aplikasi berbasis *Computer Vision* yang terintegrasi dengan kamera pengawas (CCTV) untuk melacak dan mengklasifikasikan entitas manusia secara otomatis. Menggunakan algoritma **YOLO11** dan pelacak **BotSORT**, sistem ini mampu menghitung jumlah pengunjung keluar-masuk serta mengklasifikasikan mereka menjadi **Pengunjung**, **Pembeli**, dan **Staf** secara *real-time*. 

Klasifikasi ini murni berbasis analisis *Dwell Time* (durasi berdiri) pada *Region of Interest* (ROI) yang dapat diatur secara dinamis, sehingga sistem bekerja efisien tanpa memerlukan pengenalan wajah (*Facial Recognition*) maupun identifikasi seragam.

---

### ✨ Spesifikasi dan Fitur Utama
1. **Deteksi Objek Real-Time:** Menggunakan model pre-trained YOLO11 yang dikalibrasi untuk mengenali manusia (Person/Class 0) secara presisi pada sudut pandang CCTV minimarket.
2. **Pelacakan ID Presisi Tinggi (BotSORT):** Mengimplementasikan tracker BotSORT yang dilengkapi dengan sistem memori dinamis (anti-bocor) untuk mempertahankan ID pelacakan meskipun objek saling tumpang tindih (*occlusion*).
3. **Penghitung Garis Masuk/Keluar Virtual:** Algoritma persilangan vektor berdasarkan pusat koordinat tubuh (*centroid*). Mendukung fleksibilitas orientasi garis (Vertikal maupun Horizontal) dan arah masuk yang dapat dikonfigurasi.
4. **Klasifikasi Berbasis Spasial & Waktu (*Dwell Time*):**
   - 🟩 **Pengunjung:** Objek terdeteksi di area umum (Default).
   - 🟧 **Pembeli:** Objek berada di dalam **Zona Kasir** melebihi batas waktu toleransi.
   - 🟦 **Staf:** Objek berada di dalam **Zona Staf** melebihi batas waktu toleransi.
5. **Dashboard Interaktif Berbasis Web (Streamlit):** Pengguna dapat mengatur kalibrasi *Region of Interest* (ROI), posisi garis batas, batas waktu (*limit timer*), dan memonitor CCTV beserta matriks data secara langsung tanpa perlu mengubah kode inti.
6. **Smart UI Bounding Box:**
   Dilengkapi logika pengaman (*clamping*) agar teks ID/Label pengunjung tidak terpotong atau menghilang saat pengunjung berada di ujung/tepi batas frame kamera.
7. **Database Logging Automatis:** Mencatat seluruh riwayat aktivitas (Masuk/Keluar, Pembeli Baru, Staf Terdeteksi) ke dalam *Database* (SQLite) yang dirender otomatis sebagai tabel di *dashboard*.

---

## 💻 Persyaratan Sistem (*Requirements*)
Sistem ini dieksekusi secara lokal (*Edge Computing*) dan membutuhkan spesifikasi dasar sebagai berikut:

**Perangkat Keras (*Hardware*):**
- CPU: Prosesor modern (Core i3/Ryzen 3 ke atas).
- GPU (Opsional): Disarankan menggunakan NVIDIA GPU (mendukung CUDA) untuk mendapatkan FPS (*framerate*) maksimum.
- RAM: Minimal 4 GB.

**Perangkat Lunak (*Software*):**
- OS: Windows 10/11, macOS, atau Linux.
- Python: Versi 3.9, 3.10, 3.11, atau 3.12.

**Dependensi Library Utama:**
- `ultralytics` (YOLO11 Engine)
- `opencv-python` (Computer Vision & Geometry Logic)
- `streamlit` (Web Dashboard & UI)
- `numpy` (Matriks Komputasi)

---

## 🚀 Cara Setup dan Instalasi

**1. Persiapkan Repositori Proyek**
Unduh (Download ZIP) atau *clone* direktori proyek ini ke komputer Anda, lalu buka terminal (atau *Command Prompt/PowerShell* pada Windows) dan arahkan ke folder proyek tersebut:
```bash
cd path/ke/folder/SmartCounter-Koperasi