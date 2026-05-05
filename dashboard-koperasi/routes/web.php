<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\VisitorLogController;

// Halaman Utama Dashboard
Route::get('/', [VisitorLogController::class, 'index']);

// Jalur Khusus API Data Grafik
Route::get('/api/chart-data', [VisitorLogController::class, 'getChartData']);