import cv2
import math
import time
import csv
import os
from ultralytics import YOLO
import argparse

# ---------- Configuration ----------
MODEL_PATH = "yolov8n.pt"
SPEED_LIMIT_KPH = 3.0
PIXELS_PER_METER = 100
ALLOWED_CLASSES = [0, 1, 2, 3, 5, 7]  # person, bicycle, car, motorcycle, bus, truck
SCREENSHOT_DIR = "screenshots"
CSV_PATH = "speed_log.csv"
SCREENSHOT_TIMEOUT = 3  # seconds in view before fallback capture
IDLE_TIME_BEFORE_FINALIZE = 1  # seconds since last seen


# ---------- Setup ----------
def setup_environment():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "object_id", "class", "speed_kph", "screenshot_path"])


def initialize_tracker():
    return {}, {}, {}, {}, {}, {}, {}, {}


# ---------- Detection Functions ----------
def compute_speed(prev_center, curr_center, fps):
    dx = curr_center[0] - prev_center[0]
    dy = curr_center[1] - prev_center[1]
    pixel_distance = math.hypot(dx, dy)

    if pixel_distance < 3:  # Jitter threshold in pixels
        return 0.0

    meters_moved = pixel_distance / PIXELS_PER_METER
    speed_mps = meters_moved * fps
    return speed_mps * 3.6  # km/h


def save_screenshot(frame, box, obj_id, class_name, speed_kph):
    timestamp = int(time.time())
    filename = f"{class_name}_id{obj_id}_speed{int(speed_kph)}_{timestamp}.jpg"
    path = os.path.join(SCREENSHOT_DIR, filename)
    cv2.imwrite(path, frame)
    return path, timestamp


def log_to_csv(timestamp, obj_id, class_name, speed_kph, screenshot_path):
    with open(CSV_PATH, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, obj_id, class_name, round(speed_kph, 2), screenshot_path])


def parse_args():
    parser = argparse.ArgumentParser(description="YOLOv8 Speed Tracker")
    parser.add_argument(
        "--video",
        type=str,
        help="Path to a video file. If not provided, webcam will be used."
    )
    return parser.parse_args()


# ---------- Main Loop ----------
def run_speed_tracker(source=0):
    model = YOLO(MODEL_PATH)
    cap = cv2.VideoCapture(source)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    # Initialize state trackers
    object_history, max_speeds, screenshot_taken, first_seen, last_updated, screenshot_finalized, box_cache, speed_history = initialize_tracker()
    class_names = model.model.names

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model.track(frame, persist=True)
        current_time = time.time()

        # Get frame dimensions and center zone
        frame_height, frame_width = frame.shape[:2]
        center_x = frame_width // 2
        center_y = (frame_height // 2) - 100

        # Define photo zone dimensions in pixels (5m x 5m)
        zone_width_pixels = int(PIXELS_PER_METER * 5)
        zone_height_pixels = int(PIXELS_PER_METER * 5)
        zone_left = max(center_x - zone_width_pixels // 2, 0)
        zone_right = min(center_x + zone_width_pixels // 2, frame_width)
        zone_top = max(center_y - zone_height_pixels // 2, 0)
        zone_bottom = min(center_y + zone_height_pixels // 2, frame_height)

        # Define center of photo zone and margin
        zone_center_x = (zone_left + zone_right) // 2
        zone_center_y = (zone_top + zone_bottom) // 2
        center_tolerance = int(PIXELS_PER_METER * 0.5)  # 0.5 meter margin

        # Draw reference overlays
        cv2.line(frame, (0, center_y), (frame_width, center_y), (255, 0, 0), 2)
        cv2.line(frame, (center_x, 0), (center_x, frame_height), (255, 0, 0), 2)

        # Draw reference 1-meter box
        box_size = int(PIXELS_PER_METER)
        top_left = (center_x - box_size // 2, center_y - box_size // 2)
        bottom_right = (center_x + box_size // 2, center_y + box_size // 2)
        cv2.rectangle(frame, top_left, bottom_right, (0, 255, 0), 2)
        cv2.putText(frame, "1 meter reference", (top_left[0], top_left[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Draw ground line 100 pixels below 1-meter reference
        ground_y = center_y + 100
        cv2.line(frame, (0, ground_y), (frame_width, ground_y), (0, 255, 255), 2)
        cv2.putText(frame, "Ground Line", (10, ground_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Draw square photo zone (5m x 5m centered)
        cv2.rectangle(frame,
                      (zone_left, zone_top),
                      (zone_right, zone_bottom),
                      (0, 0, 255), 2)
        cv2.putText(frame, "Photo Zone", (zone_left, zone_top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        if results[0].boxes.id is not None:
            ids = results[0].boxes.id.cpu().numpy()
            boxes = results[0].boxes.xyxy.cpu().numpy()
            class_ids = results[0].boxes.cls.cpu().numpy()

            for obj_id, box, cls_id in zip(ids, boxes, class_ids):
                cls_id = int(cls_id)
                if cls_id not in ALLOWED_CLASSES:
                    continue

                x1, y1, x2, y2 = map(int, box)
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                center = (cx, cy)
                class_name = class_names[cls_id]

                at_center = (
                    abs(cx - zone_center_x) <= center_tolerance and
                    abs(cy - zone_center_y) <= center_tolerance
                )

                if obj_id not in object_history:
                    object_history[obj_id] = center
                    max_speeds[obj_id] = 0
                    screenshot_taken[obj_id] = False
                    screenshot_finalized[obj_id] = False
                    first_seen[obj_id] = current_time
                    box_cache[obj_id] = box
                    speed_history[obj_id] = []
                    continue

                prev_center = object_history[obj_id]
                speed_kph = compute_speed(prev_center, center, fps)

                if speed_kph <= SPEED_LIMIT_KPH:
                    continue

                object_history[obj_id] = center
                last_updated[obj_id] = current_time
                box_cache[obj_id] = box
                max_speeds[obj_id] = max(max_speeds[obj_id], speed_kph)
                speed_history[obj_id].append(speed_kph)
                avg_speed = sum(speed_history[obj_id]) / len(speed_history[obj_id])

                label = f"{class_name} ID {obj_id} | Now: {speed_kph:.1f} km/h"
                font = cv2.FONT_HERSHEY_SIMPLEX
                scale = 0.6
                thickness = 2
                (text_width, text_height), _ = cv2.getTextSize(label, font, scale, thickness)
                label_x, label_y = x1, y1 - 10
                if label_y - text_height < 0:
                    label_y = y1 + text_height + 10
                cv2.rectangle(frame,
                              (label_x, label_y - text_height - 4),
                              (label_x + text_width + 6, label_y + 4),
                              (0, 0, 0), -1)
                cv2.putText(frame, label, (label_x, label_y), font, scale, (0, 255, 255), thickness)

                if speed_kph > SPEED_LIMIT_KPH and at_center and not screenshot_taken[obj_id] and not screenshot_finalized[obj_id]:
                    screenshot_path, timestamp = save_screenshot(frame, box, obj_id, class_name, speed_kph)
                    log_to_csv(timestamp, obj_id, class_name, speed_kph, screenshot_path)
                    screenshot_taken[obj_id] = True
                    screenshot_finalized[obj_id] = True

        cv2.imshow("YOLOv8 Speed Tracker", frame)
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


# ---------- Entry Point ----------
if __name__ == "__main__":
    args = parse_args()
    setup_environment()
    run_speed_tracker(args.video if args.video else 0)