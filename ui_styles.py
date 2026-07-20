import streamlit as st

def apply_custom_styles():
    st.markdown("""
        <style>
        /* MENGGANTI FONT KE PLUS JAKARTA SANS (Font Modern untuk Dashboard SaaS) */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {background-color: transparent !important;}
        
        .top-nav {
            display: flex; justify-content: space-between; align-items: center;
            background-color: #0A1628; padding: 10px 20px; border-bottom: 1px solid #1E4D8C;
            margin-top: -60px; margin-bottom: 20px; color: white; font-weight: 600;
            border-radius: 8px;
        }
        .status-live { color: #00C9A7; display: flex; align-items: center; font-size: 14px; font-weight: 700;}
        .status-live span { height: 10px; width: 10px; background-color: #00C9A7; border-radius: 50%; display: inline-block; margin-right: 8px; box-shadow: 0 0 8px #00C9A7;}
        
        .metric-card {
            background-color: #0F2040; border-left: 4px solid #1E4D8C;
            border-radius: 12px; padding: 16px; margin-bottom: 20px;
        }
        .metric-title { color: #A0AEC0; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
        .metric-value { font-size: 36px; font-weight: 700; margin-bottom: 5px; letter-spacing: -1px; }
        .val-white { color: #FFFFFF; }
        .val-teal { color: #00C9A7; }
        .val-pink { color: #D9568B; }
        .metric-sub { color: #718096; font-size: 12px; }
        
        .log-table { width: 100%; border-collapse: collapse; font-size: 13px; color: #A0AEC0;}
        .log-table th { text-align: left; padding: 12px 8px; border-bottom: 1px solid #1E4D8C; color: white; font-weight: 600;}
        .log-table td { padding: 10px 8px; border-bottom: 1px solid #0A1628; font-weight: 500;}
        .log-table tr:nth-child(even) { background-color: #0A1628; }
        .log-table tr:nth-child(odd) { background-color: #0F2040; }
        .badge-entry { background-color: rgba(0, 201, 167, 0.2); color: #00C9A7; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;}
        .badge-buyer { background-color: rgba(217, 86, 139, 0.2); color: #D9568B; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;}
        .badge-staff { background-color: rgba(30, 77, 140, 0.4); color: #82B1FF; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;}
        
        .streamlit-expanderHeader { font-weight: 600 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

def render_top_nav():
    st.markdown("""
    <div class="top-nav">
        <div style="font-size: 18px; letter-spacing: 0.5px; font-weight: 700;">Smart Counter Koperasi Merah Putih</div>
        <div style="display: flex; gap: 20px; align-items: center; color: #A0AEC0; font-weight: 500; font-size: 14px;">
            <div class="status-live"><span></span> LIVE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_log_table():
    html = '<table class="log-table"><tr><th>Waktu</th><th>ID</th><th>Peristiwa</th><th>Zona</th><th>Durasi</th></tr>'
    for log in st.session_state.recent_logs:
        badge_class = "badge-entry" if log['event'] == "Masuk" else ("badge-buyer" if log['event'] == "Pembeli Baru" else "badge-staff")
        html += f"<tr><td>{log['time']}</td><td>{log['id']}</td><td><span class='{badge_class}'>{log['event']}</span></td><td>{log['zone']}</td><td>{log['duration']}</td></tr>"
    html += '</table>'
    return html