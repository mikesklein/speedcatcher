# yolo_speed_tracker/utils/config.py
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "calibration.json")
DEFAULT_CONFIG = {
    "pixels_per_meter": 100,
    "speed_limit_kph": 3,
    "box_offset_y": 0,
    "box_offset_x": 0,
    "calib_line1_x": 200,
    "calib_line2_x": 300,
    "real_world_distance_m": 1.0,
    "capture_zone_offset_m": 0.5,
    "capture_zone_height_m": 1.0
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(controls):
    data = {key: round(var.get(), 2) for key, var in controls.items()}
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)