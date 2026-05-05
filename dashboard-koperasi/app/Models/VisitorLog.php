<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class VisitorLog extends Model
{
    protected $table = 'visitor_logs';
    public $timestamps = false; // Matikan bawaan Laravel karena kita pakai created_at sendiri
    protected $fillable = ['track_id', 'event_type', 'created_at'];
}