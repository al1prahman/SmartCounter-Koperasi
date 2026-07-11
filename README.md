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

## 💻 Requirements (Kebutuhan Sistem)

**Software:**
*   **Python:** Versi 3.11.x (Penting: Jangan gunakan versi 3.12+ agar kompatibel dengan library *Machine Learning*).
*   **XAMPP:** Dengan PHP 8.2+ dan MySQL.
*   **Node.js & npm:** Versi terbaru untuk aset *frontend*.
*   **Composer:** Untuk manajemen dependensi PHP/Laravel.
*   **Git:** Untuk *version control*.

**Hardware Minimum:**
*   Prosesor minimum Intel Core i3/i5 generasi ke-8 atau setara (disarankan yang mendukung AVX2).
*   RAM 8 GB (16 GB sangat disarankan).
*   Webcam internal laptop atau CCTV eksternal (Resolusi HD 720p).

---

## 🚀 Cara Setup & Instalasi (Local Development)

Ikuti langkah-langkah di bawah ini secara berurutan untuk menjalankan sistem di laptop baru.

### 1. Persiapan Database
1. Buka **XAMPP Control Panel**.
2. Jalankan modul **Apache** dan **MySQL**.
3. Buka *browser* dan masuk ke `http://localhost/phpmyadmin`.
4. Buat *database* baru dengan nama: `koperasi_db`.

### 2. Setup Web Dashboard (Laravel)
Buka terminal/CMD, lalu jalankan perintah berikut:
```bash
# Masuk ke folder dashboard
cd dashboard-koperasi

# Install library PHP
composer install

# Copy file environment konfigurasi
cp .env.example .env

# Buat kunci keamanan aplikasi
php artisan key:generate

# Migrasi tabel ke database koperasi_db
php artisan migrate