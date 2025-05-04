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
    config = DEFAULT_CONFIG.copy()

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
                config.update({k: loaded[k] for k in loaded if k in config})
        except Exception as e:
            print(f"⚠️ Failed to load config: {e}. Using defaults.")

    return config

def save_config(controls):
    keys_to_save = {
        "pixels_per_meter",
        "speed_limit_kph",
        "box_offset_y",
        "box_offset_x",
        "calib_line1_x",
        "calib_line2_x",
        "real_world_distance_m",
        "capture_zone_offset_m",
        "capture_zone_height_m"
    }

    data = {}

    for key in keys_to_save:
        var = controls.get(key)
        if var is None:
            continue
        try:
            value = var.get()
            if isinstance(value, (int, float)):
                data[key] = round(value, 2)
        except Exception as e:
            print(f"⚠️ Skipped key {key}: {e}")

    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)