# yolo_speed_tracker/processor.py
import cv2
import time
import argparse
from tkinter import Tk, IntVar
from ultralytics import YOLO

from utils.config import load_config, save_config
from utils.environment import setup_environment
from utils.tracking import (
    initialize_tracker,
    compute_speed,
    save_screenshot,
    log_to_csv
)
from ui.controls import create_controls, update_control_values

MODEL_PATH = "yolov8n.pt"
ALLOWED_CLASSES = [0, 1, 2, 3, 5, 7]  # person, bicycle, car, motorcycle, bus, truck

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLOv8 Speed Tracker")
    parser.add_argument("--video", type=str, help="Path to a video file. If not provided, webcam will be used.")
    args = parser.parse_args()

    setup_environment()
    source = args.video if args.video else 0
    config = load_config()

    root = Tk()
    root.title("Live Calibration")

    controls = create_controls(root, config)
    model = YOLO(MODEL_PATH)
    cap = cv2.VideoCapture(source)
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = 30 if fps is None or fps <= 0 else fps

    tracker_data = initialize_tracker()
    class_names = model.model.names

    try:
        while True:
            root.update_idletasks()
            root.update()

            ret, frame = cap.read()
            if not ret:
                break

            update_control_values(controls)

            ppm = controls['pixels_per_meter'].get()
            speed_limit_kph = controls['speed_limit_kph'].get()
            zone_size_m = controls['zone_size_m'].get()
            offset_y = controls['box_offset_y'].get()
            offset_x = controls['box_offset_x'].get()
            scale_factor = controls['box_scale'].get() / 100.0

            results = model.track(frame, persist=True)
            current_time = time.time()

            frame_height, frame_width = frame.shape[:2]
            center_x = frame_width // 2
            center_y = (frame_height // 2) - 100

            zone_pixels = int(ppm * zone_size_m)
            zone_left = max(center_x - zone_pixels // 2, 0)
            zone_right = min(center_x + zone_pixels // 2, frame_width)
            zone_top = max(center_y - zone_pixels // 2, 0)
            zone_bottom = min(center_y + zone_pixels // 2, frame_height)

            zone_center_x = (zone_left + zone_right) // 2
            zone_center_y = (zone_top + zone_bottom) // 2
            box_size = int(ppm * scale_factor)
            gy = center_y + offset_y + (box_size // 2) + int(ppm * 3.048)
            distance_below = (gy - (center_y + offset_y)) / ppm
            cv2.line(frame, (0, gy), (frame_width, gy), (255, 255, 0), 2)
            cv2.putText(frame, f"Ground Line ({distance_below:.2f}m below)", (10, gy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            cv2.rectangle(frame, (zone_left, zone_top), (zone_right, zone_bottom), (0, 0, 255), 2)
            cv2.putText(frame, "Photo Zone", (zone_left, zone_top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            box_top_left = (center_x + offset_x - box_size // 2, center_y + offset_y - box_size // 2)
            box_bottom_right = (center_x + offset_x + box_size // 2, center_y + offset_y + box_size // 2)
            cv2.rectangle(frame, box_top_left, box_bottom_right, (0, 255, 0), 2)
            cv2.putText(frame, "1 meter reference", (box_top_left[0], box_top_left[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            if results[0].boxes.id is not None:
                ids = results[0].boxes.id.cpu().numpy()
                boxes = results[0].boxes.xyxy.cpu().numpy()
                class_ids = results[0].boxes.cls.cpu().numpy()

                for obj_id, box, cls_id in zip(ids, boxes, class_ids):
                    cls_id = int(cls_id)
                    if cls_id not in ALLOWED_CLASSES:
                        continue

                    x1, y1, x2, y2 = map(int, box)
                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                    class_name = class_names[cls_id]

                    at_center = abs(cx - zone_center_x) <= int(ppm * 0.5) and abs(cy - zone_center_y) <= int(ppm * 0.5)
                    data = tracker_data

                    if obj_id not in data['object_history']:
                        data['object_history'][obj_id] = (cx, cy)
                        data['max_speeds'][obj_id] = 0
                        data['screenshot_taken'][obj_id] = False
                        data['screenshot_finalized'][obj_id] = False
                        data['first_seen'][obj_id] = current_time
                        data['box_cache'][obj_id] = box
                        data['speed_history'][obj_id] = []
                        continue

                    speed_kph = compute_speed(data['object_history'][obj_id], (cx, cy), fps, ppm)
                    if speed_kph <= speed_limit_kph:
                        continue

                    data['object_history'][obj_id] = (cx, cy)
                    data['last_updated'][obj_id] = current_time
                    data['box_cache'][obj_id] = box
                    data['max_speeds'][obj_id] = max(data['max_speeds'][obj_id], speed_kph)
                    data['speed_history'][obj_id].append(speed_kph)

                    label = f"{class_name} ID {obj_id} | {speed_kph:.1f} km/h"
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                    if not data['screenshot_taken'][obj_id] and not data['screenshot_finalized'][obj_id] and at_center:
                        path, timestamp = save_screenshot(frame, box, obj_id, class_name, speed_kph)
                        log_to_csv(timestamp, obj_id, class_name, speed_kph, path)
                        data['screenshot_taken'][obj_id] = True
                        data['screenshot_finalized'][obj_id] = True

            cv2.imshow("YOLOv8 Speed Tracker", frame)
            if cv2.waitKey(1) == 27:
                break
    except Exception:
        pass
    finally:
        save_config(controls)
        cap.release()
        cv2.destroyAllWindows()
        root.destroy()
