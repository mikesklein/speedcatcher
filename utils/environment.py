# yolo_speed_tracker/utils/environment.py
import os
import csv

SCREENSHOT_DIR = "screenshots"
CSV_PATH = "speed_log.csv"

def setup_environment():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "object_id", "class", "speed_kph", "screenshot_path"])