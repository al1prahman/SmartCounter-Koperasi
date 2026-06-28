import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import numpy as np
from io import BytesIO
from openpyxl.styles import Border, Side, Font, Alignment

# --- IMPORT MODULES KITA ---
from config import load_config, save_config
from database import fetch_today_stats, get_chart_data, get_export_data
from ui_styles import apply_custom_styles, render_top_nav, render_log_table
from vision import run_camera_loop

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Smart Counter Koperasi Merah Putih", layout="wide", initial_sidebar_state="expanded")
apply_custom_styles()
render_top_nav()
cfg = load_config()

# --- INISIALISASI SESI & RESET HARIAN ---
today_str = datetime.now().strftime('%Y-%m-%d')
if 'initialized' not in st.session_state or st.session_state.get('current_date') != today_str:
    tin, tout, tbuy = fetch_today_stats()
    st.session_state.update({
        'initialized': True, 'current_date': today_str,
        'count_in': tin, 'count_out': tout, 'count_buyer': tbuy,
        'track_states': {}, 'staff_zone_timers': {}, 'cashier_zone_timers': {},
        'staff_ids': set(), 'buyer_ids': set(), 'recent_logs': []
    })

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown('<div style="color:white; font-size:18px; font-weight:600; margin-bottom:20px;">Panel Admin<br><span style="color:#A0AEC0; font-size:12px; font-weight:400;">Tampilan Operasional</span></div>', unsafe_allow_html=True)
video_source = st.sidebar.radio("Sumber Deteksi:", ["Kamera Live", "Unggah Video (MP4)"])

video_path = None
if video_source == "Kamera Live":
    cam_index = st.sidebar.number_input("Pilih ID Kamera", min_value=0, max_value=5, value=0)
    video_path = cam_index
else:
    uploaded_file = st.sidebar.file_uploader("Unggah File Video", type=['mp4', 'avi', 'mov'])
    if uploaded_file is not None:
        with open("temp_video.mp4", "wb") as f:
            f.write(uploaded_file.read())
        video_path = "temp_video.mp4"

run_camera = st.sidebar.toggle("Mulai Deteksi", value=False)

# === FITUR EKSPOR LAPORAN EXCEL ===
st.sidebar.markdown("---")
st.sidebar.markdown('<div style="color:white; font-size:16px; font-weight:600; margin-bottom:10px;">Ekspor Laporan</div>', unsafe_allow_html=True)
date_selection = st.sidebar.date_input("Pilih Rentang Tanggal:", value=[])

show_preview = False
df_export = pd.DataFrame()

if len(date_selection) > 0:
    start_date = date_selection[0]
    end_date = date_selection[1] if len(date_selection) > 1 else date_selection[0]
    df_export = get_export_data(start_date, end_date)
    
    if not df_export.empty:
        df_export.insert(0, 'No.', range(1, len(df_export) + 1))
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Laporan KMP')
            worksheet = writer.sheets['Laporan KMP']
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
            for idx, col in enumerate(df_export.columns):
                col_letter = worksheet.cell(row=1, column=idx+1).column_letter
                max_len = max(df_export[col].astype(str).map(len).max(), len(str(col))) + 4
                worksheet.column_dimensions[col_letter].width = max_len
            for row in worksheet.iter_rows(min_row=1, max_row=worksheet.max_row, min_col=1, max_col=worksheet.max_column):
                for cell in row:
                    cell.border = thin_border
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                    if cell.row == 1: cell.font = Font(bold=True)
                        
        excel_data = output.getvalue()
        st.sidebar.download_button(
            label="Unduh Laporan", data=excel_data,
            file_name=f"Laporan_KMP_{start_date}_sd_{end_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True, type="primary"
        )
        show_preview = st.sidebar.toggle("Tampilkan Visual Laporan")
    else:
        st.sidebar.warning("Tidak ada riwayat pada tanggal tersebut.")

st.sidebar.markdown("---")

# === PENGATURAN ZONA ===
st.sidebar.subheader("Pengaturan Garis Pintu")
idx_orient = 0 if cfg["LINE_ORIENT"] == "Vertikal" else 1
LINE_ORIENT = st.sidebar.selectbox("Orientasi Garis Pintu", ["Vertikal", "Horizontal"], index=idx_orient)
if LINE_ORIENT == "Vertikal":
    LINE_POS = st.sidebar.slider("Posisi Koordinat (X)", 0, 640, cfg["LINE_POS"])
    ENTRY_DIR = st.sidebar.radio("Definisi Arah 'Masuk':", ["Kiri ke Kanan", "Kanan ke Kiri"], index=0 if cfg["ENTRY_DIR"] == "Kiri ke Kanan" else 1)
else:
    LINE_POS = st.sidebar.slider("Posisi Koordinat (Y)", 0, 480, cfg["LINE_POS"])
    ENTRY_DIR = st.sidebar.radio("Definisi Arah 'Masuk':", ["Atas ke Bawah", "Bawah ke Atas"], index=0 if cfg["ENTRY_DIR"] == "Atas ke Bawah" else 1)

with st.sidebar.expander("Konfigurasi Kotak & Waktu Tunggu", expanded=False):
    STAFF_LIMIT = st.slider("Waktu Tunggu Staf", 1, 60, cfg["STAFF_LIMIT"]) 
    BUYER_LIMIT = st.slider("Waktu Tunggu Pembeli", 1, 60, cfg["BUYER_LIMIT"]) 
    st.markdown("---")
    stf_x = st.slider("Staf: Posisi X", 0, 640, cfg["stf_x"])
    stf_y = st.slider("Staf: Posisi Y", 0, 480, cfg["stf_y"])
    stf_w = st.slider("Staf: Lebar", 50, 640, cfg["stf_w"])
    stf_h = st.slider("Staf: Tinggi", 50, 480, cfg["stf_h"])
    ksr_x = st.slider("Kasir: Posisi X", 0, 640, cfg["ksr_x"])
    ksr_y = st.slider("Kasir: Posisi Y", 0, 480, cfg["ksr_y"])
    ksr_w = st.slider("Kasir: Lebar", 50, 640, cfg["ksr_w"])
    ksr_h = st.slider("Kasir: Tinggi", 50, 480, cfg["ksr_h"])

new_cfg = {
    "LINE_ORIENT": LINE_ORIENT, "LINE_POS": LINE_POS, "ENTRY_DIR": ENTRY_DIR,
    "STAFF_LIMIT": STAFF_LIMIT, "BUYER_LIMIT": BUYER_LIMIT,
    "stf_x": stf_x, "stf_y": stf_y, "stf_w": stf_w, "stf_h": stf_h,
    "ksr_x": ksr_x, "ksr_y": ksr_y, "ksr_w": ksr_w, "ksr_h": ksr_h
}
save_config(new_cfg)

# ==========================================
# RENDER UTAMA (PREVIEW / DASHBOARD)
# ==========================================
if show_preview and not df_export.empty:
    st.markdown('<div class="metric-card"><div style="color:white; font-weight:600; font-size:20px; margin-bottom:10px;">📊 Pratinjau Laporan (Visualisasi Ekspor CSV)</div>', unsafe_allow_html=True)
    st.dataframe(df_export, use_container_width=True, hide_index=True)
    
    colA, colB = st.columns(2)
    with colA:
        fig_comp = go.Figure(data=[
            go.Bar(name='Pengunjung', x=df_export['Tanggal'].astype(str), y=df_export['Total Pengunjung'], marker_color='#00C9A7'),
            go.Bar(name='Pembeli', x=df_export['Tanggal'].astype(str), y=df_export['Total Pembeli'], marker_color='#D9568B')
        ])
        fig_comp.update_layout(title="Perbandingan Pengunjung vs Pembeli", barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#A0AEC0')
        fig_comp.update_yaxes(showgrid=True, gridcolor='rgba(30, 77, 140, 0.3)')
        st.plotly_chart(fig_comp, use_container_width=True)
        
    with colB:
        if len(df_export) > 1:
            df_sorted = df_export.sort_values(by='Total Pengunjung', ascending=True)
            fig_ext = go.Figure(go.Bar(x=df_sorted['Total Pengunjung'], y=df_sorted['Tanggal'].astype(str), orientation='h', marker_color='#82B1FF'))
            fig_ext.update_layout(title="Peringkat Hari (Paling Sepi ke Ramai)", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#A0AEC0')
            st.plotly_chart(fig_ext, use_container_width=True)
        else:
            rate = df_export.iloc[0]['Tingkat Konversi (%)']
            fig_gauge = go.Figure(go.Indicator(mode="gauge+number", value=rate, title={'text': "Tingkat Konversi", 'font': {'color': '#A0AEC0'}}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#D9568B"}}))
            fig_gauge.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font_color='#A0AEC0')
            st.plotly_chart(fig_gauge, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown('<div style="color:white; font-weight:600; font-size:16px; margin-bottom:10px;">📹 Tayangan Langsung</div>', unsafe_allow_html=True)
    FRAME_WINDOW = st.empty()
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    ph_in, ph_buy, ph_rate, ph_occ = col1.empty(), col2.empty(), col3.empty(), col4.empty()

    def update_metrics_ui():
        c_in, c_buy, c_out = st.session_state.count_in, st.session_state.count_buyer, st.session_state.count_out
        rate = round((c_buy / c_in * 100), 1) if c_in > 0 else 0
        occ = max(0, c_in - c_out) 
        ph_in.markdown(f'<div class="metric-card"><div class="metric-title">TOTAL MASUK HARI INI</div><div class="metric-value val-white">{c_in}</div></div>', unsafe_allow_html=True)
        ph_buy.markdown(f'<div class="metric-card"><div class="metric-title">TOTAL PEMBELI</div><div class="metric-value val-pink">{c_buy}</div></div>', unsafe_allow_html=True)
        ph_rate.markdown(f'<div class="metric-card"><div class="metric-title">TINGKAT KONVERSI</div><div class="metric-value val-teal">{rate}%</div></div>', unsafe_allow_html=True)
        ph_occ.markdown(f'<div class="metric-card"><div class="metric-title">PENGUNJUNG DI DALAM</div><div class="metric-value val-white">{occ}</div></div>', unsafe_allow_html=True)

    update_metrics_ui()
    df_h, df_d = get_chart_data()
    col_left, col_right = st.columns([6, 4])

    with col_left:
        st.markdown('<div style="color:white; font-weight:600; margin-bottom:10px;">Lalu Lintas Per Jam Hari Ini</div>', unsafe_allow_html=True)
        if not df_h.empty:
            fig1 = go.Figure(go.Bar(x=df_h['jam'].astype(str)+':00', y=df_h['total'], marker_color='#D9568B'))
            fig1.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#A0AEC0', margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig1, use_container_width=True)
        with st.expander("Log Aktivitas Terkini", expanded=False):
            LOG_WINDOW = st.empty()

    with col_right:
        st.markdown('<div style="color:white; font-weight:600; margin-bottom:10px;">Pengunjung vs Pembeli (7 Hari)</div>', unsafe_allow_html=True)
        if not df_d.empty:
            fig2 = go.Figure(data=[go.Bar(name='Pengunjung', x=df_d['tanggal'], y=df_d['Pengunjung'], marker_color='#00C9A7'), go.Bar(name='Pembeli', x=df_d['tanggal'], y=df_d['Pembeli'], marker_color='#D9568B')])
            fig2.update_layout(height=560, barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#A0AEC0', showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig2, use_container_width=True)

    # --- JALANKAN LOGIKA KAMERA VIA VISION.PY ---
    if run_camera and video_path is not None:
        run_camera_loop(video_path, new_cfg, FRAME_WINDOW, LOG_WINDOW, update_metrics_ui)
    else:
        with col_left:
            LOG_WINDOW.markdown(render_log_table(), unsafe_allow_html=True)