<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Smart Counter</title>
    <!-- Memanggil Tailwind CSS untuk styling modern -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Memanggil Chart.js untuk membuat grafik -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-gray-50 text-gray-800 font-sans p-6">

    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-gray-900">Sistem Cerdas Penghitung Pengunjung</h1>
            <p class="text-gray-500 mt-1">Dashboard Analitik Koperasi Merah Putih</p>
        </div>

        <!-- Stat Cards (Menggunakan data dari Controller) -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <!-- Card Pengunjung -->
            <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100 border-l-4 border-l-green-500">
                <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-wider">Total Masuk (Hari Ini)</h3>
                <div class="mt-2 text-3xl font-bold text-gray-900">{{ $totalMasuk }} <span class="text-sm font-medium text-gray-400">Orang</span></div>
            </div>

            <!-- Card Pembeli -->
            <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100 border-l-4 border-l-orange-500">
                <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-wider">Total Pembeli (Hari Ini)</h3>
                <div class="mt-2 text-3xl font-bold text-gray-900">{{ $totalPembeli }} <span class="text-sm font-medium text-gray-400">Orang</span></div>
            </div>

            <!-- Card Conversion Rate -->
            <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100 border-l-4 border-l-blue-500">
                <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-wider">Conversion Rate</h3>
                <div class="mt-2 text-3xl font-bold text-gray-900">{{ $conversionRate }}<span class="text-xl">%</span></div>
            </div>
        </div>

        <!-- Charts Area -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Grafik Line: Trafik Jam -->
            <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
                <h3 class="text-lg font-bold text-gray-800 mb-4">Trafik Pengunjung per Jam (Hari Ini)</h3>
                <canvas id="hourlyChart" height="250"></canvas>
            </div>

            <!-- Grafik Bar: Perbandingan 7 Hari -->
            <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
                <h3 class="text-lg font-bold text-gray-800 mb-4">Pengunjung vs Pembeli (7 Hari Terakhir)</h3>
                <canvas id="dailyChart" height="250"></canvas>
            </div>
        </div>
    </div>

    <!-- Script JavaScript untuk memanggil API dan menggambar Chart -->
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Mengambil data dari API yang kita buat di Step 13
            fetch('/api/chart-data')
                .then(response => response.json())
                .then(data => {
                    
                    // 1. Menggambar Line Chart (Trafik Per Jam)
                    const ctxHourly = document.getElementById('hourlyChart').getContext('2d');
                    new Chart(ctxHourly, {
                        type: 'line',
                        data: {
                            labels: data.hourly.labels,
                            datasets: [{
                                label: 'Jumlah Masuk',
                                data: data.hourly.data,
                                borderColor: '#22c55e', // Warna Hijau
                                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                                borderWidth: 3,
                                tension: 0.4, // Membuat garis melengkung halus
                                fill: true
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
                        }
                    });

                    // 2. Menggambar Bar Chart (Perbandingan 7 Hari)
                    const ctxDaily = document.getElementById('dailyChart').getContext('2d');
                    new Chart(ctxDaily, {
                        type: 'bar',
                        data: {
                            labels: data.daily.labels,
                            datasets: [
                                {
                                    label: 'Pengunjung',
                                    data: data.daily.visitors,
                                    backgroundColor: '#22c55e', // Hijau
                                    borderRadius: 4
                                },
                                {
                                    label: 'Pembeli',
                                    data: data.daily.buyers,
                                    backgroundColor: '#f97316', // Oranye
                                    borderRadius: 4
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
                        }
                    });

                })
                .catch(error => console.error('Error fetching chart data:', error));
        });
    </script>
</body>
</html>