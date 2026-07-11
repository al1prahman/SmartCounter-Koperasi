# 🛒 Smart Counter & Dwell Time Analysis - Koperasi Merah Putih

## 📖 Deskripsi Singkat
**Sistem Smart Counter dan Analisis Dwell Time** adalah aplikasi berbasis *Computer Vision* yang terintegrasi dengan kamera pengawas (CCTV) untuk melacak dan mengklasifikasikan entitas manusia secara otomatis. Menggunakan algoritma **YOLO11** dan pelacak **BotSORT**, sistem ini mampu menghitung jumlah pengunjung keluar-masuk serta mengklasifikasikan mereka menjadi **Pengunjung**, **Pembeli**, dan **Staf** secara *real-time*. 

Klasifikasi ini murni berbasis analisis *Dwell Time* (durasi berdiri) pada *Region of Interest* (ROI) yang dapat diatur secara dinamis, sehingga sistem bekerja efisien tanpa memerlukan pengenalan wajah (*Facial Recognition*) maupun identifikasi seragam.

---

## 📌 Spesifikasi & Fitur Utama
Sistem ini terdiri dari dua modul utama: **AI Camera Processing** (Python) dan **Web Dashboard** (Laravel 12).

1. **Visitor Counting (In/Out):** Menggunakan garis virtual vertikal untuk menghitung total pengunjung masuk (kiri ke kanan) dan keluar (kanan ke kiri) dengan zona toleransi anti *double-counting*.
2. **Staff Filtering (Geofencing):** Mendeteksi dan mengabaikan staf koperasi dari hitungan pengunjung jika mereka berada di dalam "Zona Staf" selama lebih dari 30 detik (*dwell-time analysis*).
3. **Buyer Estimation (ROI Cashier):** Menganalisis *dwell-time* pengunjung di "Zona Kasir". Jika pengunjung mengantre lebih dari 20 detik secara berturut-turut, sistem otomatis mengonversi status mereka menjadi "Pembeli".
4. **Real-time Database Logging:** Mencatat setiap kejadian lalu lintas dan transaksi ke dalam MySQL (sedang dikembangkan).

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