import cv2
import math
import time
import csv
import os
from ultralytics import YOLO
import argparse
from utils.tracking import initialize_tracker, compute_speed, save_screenshot, log_to_csv
from utils.environment import SCREENSHOT_DIR, CSV_PATH # Ensure these are from environment
from utils.config import load_config
from utils.core_processing import process_detected_object
from utils.constants import (
    CENTER_LINE_COLOR, REFERENCE_BOX_COLOR, REFERENCE_BOX_TEXT_COLOR, 
    GROUND_LINE_COLOR_SC, PHOTO_ZONE_COLOR, PHOTO_ZONE_TEXT_COLOR,
    FONT_HERSHEY_SIMPLEX, FONT_SCALE_SMALL, LINE_THICKNESS_DEFAULT,
    CENTER_TOLERANCE_METERS
)

# ---------- Configuration (Now loaded from config file) ----------
# MODEL_PATH = "yolov8n.pt"
# SPEED_LIMIT_KPH = 3.0
# PIXELS_PER_METER = 100
# ALLOWED_CLASSES = [0, 1, 2, 3, 5, 7]
# SCREENSHOT_TIMEOUT = 3
# IDLE_TIME_BEFORE_FINALIZE = 1


# ---------- Setup ----------
def setup_environment(): # This function now solely relies on SCREENSHOT_DIR, CSV_PATH from environment
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "object_id", "class", "speed_kph", "screenshot_path"])


def parse_args():
    parser = argparse.ArgumentParser(description="YOLOv8 Speed Tracker")
    parser.add_argument(
        "--video",
        type=str,
        help="Path to a video file. If not provided, webcam will be used."
    )
    return parser.parse_args()


# ---------- Helper Functions for Main Loop ----------
def initialize_video_source(source_path_or_id):
    cap = cv2.VideoCapture(source_path_or_id)
    if not cap.isOpened():
        raise IOError(f"Cannot open video source: {source_path_or_id}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30  # Default to 30 if FPS not available
    return cap, fps

def draw_reference_overlays(frame, pixels_per_meter, zone_size_m):
    frame_height, frame_width = frame.shape[:2]
    center_x = frame_width // 2
    # This offset might need to be part of config or a fixed UI choice. For now, keep as is.
    center_y = (frame_height // 2) - 100

    # Draw reference center lines
    cv2.line(frame, (0, center_y), (frame_width, center_y), CENTER_LINE_COLOR, LINE_THICKNESS_DEFAULT)
    cv2.line(frame, (center_x, 0), (center_x, frame_height), CENTER_LINE_COLOR, LINE_THICKNESS_DEFAULT)

    # Draw 1-meter reference box (assuming it's centered at center_x, center_y)
    box_size = int(pixels_per_meter) # 1 meter
    top_left = (center_x - box_size // 2, center_y - box_size // 2)
    bottom_right = (center_x + box_size // 2, center_y + box_size // 2)
    cv2.rectangle(frame, top_left, bottom_right, REFERENCE_BOX_COLOR, LINE_THICKNESS_DEFAULT)
    cv2.putText(frame, "1 meter reference", (top_left[0], top_left[1] - 10),
                FONT_HERSHEY_SIMPLEX, FONT_SCALE_SMALL, REFERENCE_BOX_TEXT_COLOR, LINE_THICKNESS_DEFAULT)

    # Draw ground line (100 pixels below 1-meter reference's center_y)
    ground_y = center_y + 100 # This fixed offset might need review or config
    cv2.line(frame, (0, ground_y), (frame_width, ground_y), GROUND_LINE_COLOR_SC, LINE_THICKNESS_DEFAULT)
    cv2.putText(frame, "Ground Line", (10, ground_y - 10),
                FONT_HERSHEY_SIMPLEX, FONT_SCALE_SMALL, GROUND_LINE_COLOR_SC, LINE_THICKNESS_DEFAULT)

    # Define and Draw photo zone (using zone_size_m)
    zone_width_pixels = int(pixels_per_meter * zone_size_m)
    zone_height_pixels = int(pixels_per_meter * zone_size_m) # Assuming square zone from zone_size_m

    zone_left = max(center_x - zone_width_pixels // 2, 0)
    zone_right = min(center_x + zone_width_pixels // 2, frame_width)
    zone_top = max(center_y - zone_height_pixels // 2, 0) # Centered around center_y
    zone_bottom = min(center_y + zone_height_pixels // 2, frame_height)

    cv2.rectangle(frame, (zone_left, zone_top), (zone_right, zone_bottom), PHOTO_ZONE_COLOR, LINE_THICKNESS_DEFAULT)
    cv2.putText(frame, "Photo Zone", (zone_left, zone_top - 10),
                FONT_HERSHEY_SIMPLEX, FONT_SCALE_SMALL, PHOTO_ZONE_TEXT_COLOR, LINE_THICKNESS_DEFAULT)
    
    # Return calculated zone centers and tolerance for object processing
    zone_center_x = (zone_left + zone_right) // 2
    zone_center_y = (zone_top + zone_bottom) // 2
    center_tolerance = int(pixels_per_meter * CENTER_TOLERANCE_METERS)
    return zone_center_x, zone_center_y, center_tolerance

# process_object function is now removed and imported from utils.core_processing


# ---------- Main Loop ----------
def run_speed_tracker(source_arg):
    config = load_config()
    model = YOLO(config['model_path'])
    
    try:
        cap, fps = initialize_video_source(source_arg if source_arg is not None else 0)
    except IOError as e:
        print(e)
        return

    tracker_data = initialize_tracker() # from utils.tracking
    class_names = model.model.names

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame or video ended.")
            break
        
        current_time = time.time()

        # Draw reference overlays and get zone parameters
        zone_center_x, zone_center_y, center_tolerance = draw_reference_overlays(
            frame, 
            config['pixels_per_meter'], 
            config['zone_size_m']
        )
        
        results = model.track(frame, persist=True, verbose=False) # verbose=False to reduce console spam

        if results[0].boxes is not None and results[0].boxes.id is not None:
            ids = results[0].boxes.id.cpu().numpy()
            boxes = results[0].boxes.xyxy.cpu().numpy()
            class_ids = results[0].boxes.cls.cpu().numpy()

            for obj_id, box, cls_id in zip(ids, boxes, class_ids):
                process_detected_object( # Renamed function call
                    obj_id, box, cls_id, class_names, tracker_data, 
                    current_time, frame, config, fps, 
                    zone_center_x, zone_center_y, center_tolerance
                )
        
        cv2.imshow("YOLOv8 Speed Tracker", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC key
            break

    cap.release()
    cv2.destroyAllWindows()


# ---------- Entry Point ----------
if __name__ == "__main__":
    args = parse_args()
    setup_environment()
    run_speed_tracker(args.video) # Pass args.video (which can be None)