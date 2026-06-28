import json
import os

CONFIG_FILE = "ui_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "LINE_ORIENT": "Vertikal", "LINE_POS": 320, "ENTRY_DIR": "Kiri ke Kanan",
        "STAFF_LIMIT": 10, "BUYER_LIMIT": 10,
        "stf_x": 50, "stf_y": 50, "stf_w": 200, "stf_h": 300,
        "ksr_x": 380, "ksr_y": 50, "ksr_w": 200, "ksr_h": 300
    }

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)