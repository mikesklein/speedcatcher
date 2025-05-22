# yolo_speed_tracker/utils/config.py
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "calibration.json")
DEFAULT_CONFIG = {
    "pixels_per_meter": 100,
    "speed_limit_kph": 3.0,  # Ensure float
    "box_offset_y": 0,
    "box_offset_x": 0,
    "calib_line1_x": 200.0, # Ensure float
    "calib_line2_x": 300.0, # Ensure float
    "real_world_distance_m": 1.0,
    "capture_zone_offset_m": 0.5,
    "capture_zone_height_m": 1.0,
    "zone_size_m": 5.0, # Default to 5 meters for the photo zone size

    # New additions for speedcatcher.py (and potentially GUI later)
    "model_path": "yolov8n.pt",
    "allowed_classes": [0, 1, 2, 3, 5, 7],  # person, bicycle, car, motorcycle, bus, truck
    "screenshot_timeout": 3, # seconds
    "idle_time_before_finalize": 1, # seconds
}

def load_config():
    config = DEFAULT_CONFIG.copy() # Start with defaults

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
                # Update only known keys from DEFAULT_CONFIG to avoid polluting config with old/unexpected keys from json
                for key in config.keys():
                    if key in loaded:
                        config[key] = loaded[key]
        except Exception as e:
            print(f"⚠️ Failed to load config: {e}. Using defaults.")
    else:
        print(f"ℹ️ Config file not found at {CONFIG_FILE}. Using default settings and creating file.")
        # Save default config if file not found
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)

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
        "capture_zone_height_m",
        "zone_size_m",
        "model_path",
        "allowed_classes",
        "screenshot_timeout",
        "idle_time_before_finalize"
    }

    data = {}

    for key in keys_to_save:
        var = controls.get(key)
        if var is None:
            print(f"ℹ️ No control variable found for key: {key}. Skipping save for this key.")
            continue
        try:
            value = var.get() # This is for Tkinter variables
            # Handle different types of values from Tkinter controls
            if isinstance(value, (int, float)):
                data[key] = round(value, 2)
            elif isinstance(value, str):
                # For strings like model_path or potentially comma-separated lists if not using Listbox
                data[key] = value
            elif isinstance(value, list): # For allowed_classes if Listbox or similar returns a list
                data[key] = value
            else: # Fallback for other types, e.g. boolean if Checkbutton used
                 # For allowed_classes, if it's a string from an Entry, it needs parsing.
                 # Assuming here that the control for 'allowed_classes' would return a list or a string that needs parsing.
                 # For simplicity, if it's a string that should be a list of ints (e.g., "0,1,2,3"),
                 # it needs specific handling not shown here, as var.get() on an Entry gives string.
                 # Current ui/controls.py doesn't have a control for allowed_classes yet.
                 # For now, we'll assume if it's not int/float/str/list, it's not directly savable by this generic logic.
                print(f"ℹ️ Value type for key {key} is {type(value)}, not saving directly. Implement specific handling if needed.")

        except Exception as e:
            print(f"⚠️ Skipped saving key {key} due to error: {e}")


    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)