# yolo_speed_tracker/main.py
import cv2
import time
import argparse
import traceback
from tkinter import Tk
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
    last_frame = None
    prev_time = time.time()

    try:
        while True:
            root.update_idletasks()
            root.update()

            update_control_values(controls)

            if not controls['paused'].get():
                ret, frame = cap.read()
                if not ret:
                    break
                last_frame = frame
            else:
                if last_frame is None:
                    continue
                frame = last_frame.copy()
                cv2.putText(frame, "PAUSED", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

            # === FPS calculation ===
            curr_time = time.time()
            fps_display = f"FPS: {1 / (curr_time - prev_time):.1f}"
            prev_time = curr_time
            cv2.putText(frame, fps_display, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            ppm = controls['pixels_per_meter'].get()
            speed_limit_kph = controls['speed_limit_kph'].get()
            offset_y = controls['box_offset_y'].get()
            offset_x = controls['box_offset_x'].get()
            capture_zone_offset_m = controls['capture_zone_offset_m'].get()
            capture_zone_height_m = controls['capture_zone_height_m'].get()

            results = model.track(frame, persist=True)
            current_time = time.time()

            frame_height, frame_width = frame.shape[:2]
            center_x = frame_width // 2
            center_y = (frame_height // 2) - 100

            box_height = int(ppm * 1.0)
            reference_bottom_y = center_y + offset_y + box_height // 2

            # Ground Line
            gy = int(reference_bottom_y + ppm * 1.0)
            cv2.line(frame, (0, gy), (frame_width, gy), (255, 255, 0), 2)
            cv2.putText(frame, "Ground Line (1.00m below)", (10, gy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Speed Capture Zone
            capture_zone_top = int(reference_bottom_y + capture_zone_offset_m * ppm)
            capture_zone_bottom = int(capture_zone_top + capture_zone_height_m * ppm)
            cv2.rectangle(frame, (0, capture_zone_top), (frame_width, capture_zone_bottom), (255, 0, 255), 2)
            cv2.putText(frame, "Speed Capture Zone", (10, capture_zone_top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)

            # Calibration lines
            x1 = int(controls['calib_line1_x'].get())
            x2 = int(controls['calib_line2_x'].get())
            real_world_m = float(controls['real_world_distance_m'].get())
            pixel_distance = abs(x2 - x1)

            cv2.line(frame, (x1, 0), (x1, frame_height), (0, 255, 255), 1)
            cv2.line(frame, (x2, 0), (x2, frame_height), (0, 255, 255), 1)
            cv2.putText(frame, "Calib Line 1", (x1 + 5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(frame, "Calib Line 2", (x2 + 5, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            if real_world_m > 0:
                ppm_estimated = pixel_distance / real_world_m
                cv2.putText(frame, f"Est. PPM: {ppm_estimated:.1f}", (10, frame_height - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            # Detection loop
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

                    in_capture_zone = capture_zone_top <= cy <= capture_zone_bottom
                    in_horizontal_center = abs(cx - center_x) <= int(ppm * 0.5)
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

                    speed_kph, direction = compute_speed(data['object_history'][obj_id], (cx, cy), fps, ppm)
                    data['object_history'][obj_id] = (cx, cy)
                    data['last_updated'][obj_id] = current_time
                    data['box_cache'][obj_id] = box
                    data['max_speeds'][obj_id] = max(data['max_speeds'][obj_id], speed_kph)
                    data['speed_history'][obj_id].append(speed_kph)

                    label = f"{class_name} ID {obj_id} | {speed_kph:.1f} km/h"
                    (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(frame, (x1, y1 - text_height - baseline - 10),
                                  (x1 + text_width, y1 - 10), (0, 0, 0), thickness=-1)
                    cv2.putText(frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                    if (direction == "right" and speed_kph > speed_limit_kph and
                        in_capture_zone and in_horizontal_center and
                        not data['screenshot_taken'][obj_id] and not data['screenshot_finalized'][obj_id]):
                        path, timestamp = save_screenshot(frame, box, obj_id, class_name, speed_kph)
                        log_to_csv(timestamp, obj_id, class_name, speed_kph, path, direction)
                        data['screenshot_taken'][obj_id] = True
                        data['screenshot_finalized'][obj_id] = True

            cv2.imshow("YOLOv8 Speed Tracker", frame)
            if cv2.waitKey(1) == 27:
                break

    except Exception as e:
        print("🔥 Error in main loop:", e)
        traceback.print_exc()

    finally:
        try:
            save_config(controls)
        except Exception as e:
            print("⚠️ Failed to save config:", e)

        try:
            cap.release()
        except Exception:
            pass

        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        try:
            root.destroy()
        except Exception:
            pass