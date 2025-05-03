# yolo_speed_tracker/utils/tracking.py
import math
import time
import os
import csv
import cv2
from .environment import SCREENSHOT_DIR, CSV_PATH

def initialize_tracker():
    return {
        "object_history": {},
        "max_speeds": {},
        "screenshot_taken": {},
        "first_seen": {},
        "last_updated": {},
        "screenshot_finalized": {},
        "box_cache": {},
        "speed_history": {}
    }

def compute_speed(prev_center, curr_center, fps, pixels_per_meter):
    dx = curr_center[0] - prev_center[0]
    dy = curr_center[1] - prev_center[1]
    pixel_distance = math.hypot(dx, dy)
    if pixel_distance < 3:
        return 0.0, None  # Ignore tiny movements

    meters_moved = pixel_distance / pixels_per_meter
    speed_mps = meters_moved * fps
    direction = "right" if dx > 0 else "left"
    return speed_mps * 3.6, direction  # speed in km/h and direction

def save_screenshot(frame, box, obj_id, class_name, speed_kph):
    timestamp = int(time.time())
    filename = f"{class_name}_id{obj_id}_speed{int(speed_kph)}_{timestamp}.jpg"
    path = os.path.join(SCREENSHOT_DIR, filename)
    cv2.imwrite(path, frame)
    return path, timestamp

def log_to_csv(timestamp, obj_id, class_name, speed_kph, screenshot_path, direction=None):
    with open(CSV_PATH, mode="a", newline="") as file:
        writer = csv.writer(file)
        row = [timestamp, obj_id, class_name, round(speed_kph, 2), screenshot_path]
        if direction is not None:
            row.append(direction)
        writer.writerow(row)