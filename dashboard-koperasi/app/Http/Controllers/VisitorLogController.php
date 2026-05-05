<?php

namespace App\Http\Controllers;

use App\Models\VisitorLog;
use Carbon\Carbon;
use Illuminate\Http\Request;

class VisitorLogController extends Controller
{
    // --- FUNGSI 1: Untuk mengirim angka ke Kartu Statistik (Stat Card) ---
    public function index()
    {
        $today = Carbon::today();

        $totalMasuk = VisitorLog::where('event_type', 'Masuk')
            ->whereDate('created_at', $today)
            ->count();

        $totalPembeli = VisitorLog::where('event_type', 'Pembeli Baru')
            ->whereDate('created_at', $today)
            ->count();

        $conversionRate = 0;
        if ($totalMasuk > 0) {
            $conversionRate = round(($totalPembeli / $totalMasuk) * 100, 1);
        }

        return view('dashboard', compact('totalMasuk', 'totalPembeli', 'conversionRate'));
    }

    // --- FUNGSI 2: API Route untuk Data Grafik Chart.js (Step 13) ---
    public function getChartData()
    {
        $today = Carbon::today();
        $last7Days = Carbon::today()->subDays(6);

        // A. Trafik Pengunjung Per Jam (Khusus Hari Ini)
        $hourlyTraffic = VisitorLog::selectRaw('HOUR(created_at) as hour, count(*) as total')
            ->where('event_type', 'Masuk')
            ->whereDate('created_at', $today)
            ->groupBy('hour')
            ->pluck('total', 'hour')
            ->toArray();
        
        $hourlyLabels = [];
        $hourlyData = [];
        // Jam operasional: 08:00 - 17:00
        for ($i = 8; $i <= 17; $i++) { 
            $hourlyLabels[] = str_pad($i, 2, '0', STR_PAD_LEFT) . ':00';
            $hourlyData[] = $hourlyTraffic[$i] ?? 0;
        }

        // B. Statistik Pengunjung vs Pembeli (7 Hari Terakhir)
        $dailyMasuk = VisitorLog::selectRaw('DATE(created_at) as date, count(*) as total')
            ->where('event_type', 'Masuk')
            ->where('created_at', '>=', $last7Days)
            ->groupBy('date')
            ->pluck('total', 'date')
            ->toArray();

        $dailyPembeli = VisitorLog::selectRaw('DATE(created_at) as date, count(*) as total')
            ->where('event_type', 'Pembeli Baru')
            ->where('created_at', '>=', $last7Days)
            ->groupBy('date')
            ->pluck('total', 'date')
            ->toArray();

        $dailyLabels = [];
        $dataMasuk = [];
        $dataPembeli = [];

        // Looping 7 hari ke belakang
        for ($i = 6; $i >= 0; $i--) {
            $date = Carbon::today()->subDays($i)->format('Y-m-d');
            $dailyLabels[] = Carbon::parse($date)->format('d M');
            $dataMasuk[] = $dailyMasuk[$date] ?? 0;
            $dataPembeli[] = $dailyPembeli[$date] ?? 0;
        }

        return response()->json([
            'hourly' => [
                'labels' => $hourlyLabels,
                'data' => $hourlyData
            ],
            'daily' => [
                'labels' => $dailyLabels,
                'visitors' => $dataMasuk,
                'buyers' => $dataPembeli
            ]
        ]);
    }
}