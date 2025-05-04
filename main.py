import cv2
import time
import math
import os
import csv
import argparse
import traceback
from tkinter import Tk
from ultralytics import YOLO

from utils.config import load_config, save_config
from utils.environment import setup_environment, SCREENSHOT_DIR, CSV_PATH
from ui.controls import create_controls, update_control_values

MODEL_PATH = "yolov8n.pt"
ALLOWED_CLASSES = [2, 3, 5, 7]  # person, bicycle, car, motorcycle, bus, truck

def initialize_tracker():
    return {
        "object_history": {},
        "max_speeds": {},
        "screenshot_taken": {},
        "first_seen": {},
        "last_updated": {},
        "screenshot_finalized": {},
        "box_cache": {},
        "speed_history": {},
        "last_time": {}
    }

def compute_speed(prev_center, curr_center, time_elapsed, pixels_per_meter):
    dx = curr_center[0] - prev_center[0]
    dy = curr_center[1] - prev_center[1]
    pixel_distance = math.hypot(dx, dy)
    if pixel_distance < 3 or time_elapsed <= 0:
        return 0.0, None
    meters_moved = pixel_distance / pixels_per_meter
    speed_mps = meters_moved / time_elapsed
    direction = "right" if dx > 0 else "left"
    return speed_mps * 3.6 * 2, direction  # km/h

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

def initialize_video_source(video_path):
    cap = cv2.VideoCapture(video_path if video_path else 4)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    return cap

def read_and_process_frame(cap, last_frame, paused):
    if not paused:
        ret, frame = cap.read()
        if not ret:
            return None, None, last_frame
        # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # equalized = cv2.equalizeHist(gray)
        # frame = cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR)
        return frame, False, frame
    else:
        if last_frame is None:
            return None, True, last_frame
        frame = last_frame.copy()
        cv2.putText(frame, "PAUSED", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        return frame, True, last_frame

def main_loop(cap, model, controls, tracker_data, class_names, root, is_live):
    last_frame = None
    prev_time = time.time()

    while True:
        root.update_idletasks()
        root.update()
        update_control_values(controls)
        paused = controls['paused'].get()

        frame, skip, last_frame = read_and_process_frame(cap, last_frame, paused)
        if frame is None:
            if skip:
                continue
            break

        current_time = time.time()
        if is_live:
            frame_fps = 30
        else:
            frame_fps = 1 / (current_time - prev_time)
        prev_time = current_time

        cv2.putText(frame, f"FPS: {frame_fps:.1f}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        frame_height, frame_width = frame.shape[:2]
        speed_limit_kph = controls['speed_limit_kph'].get()
        offset_y = controls['box_offset_y'].get()
        capture_zone_offset_m = controls['capture_zone_offset_m'].get()
        capture_zone_height_m = controls['capture_zone_height_m'].get()

        # Calibration lines
        x1 = int(controls['calib_line1_x'].get())
        x2 = int(controls['calib_line2_x'].get())
        real_world_m = float(controls['real_world_distance_m'].get())
        pixel_distance = abs(x2 - x1)

        use_calib = controls['use_calibration_lines'].get()

        if use_calib and real_world_m > 0 and pixel_distance > 0:
            ppm = pixel_distance / real_world_m
        else:
            ppm = controls['pixels_per_meter'].get()

        # Draw calibration lines
        cv2.line(frame, (x1, 0), (x1, frame_height), (0, 255, 255), 1)
        cv2.line(frame, (x2, 0), (x2, frame_height), (0, 255, 255), 1)
        cv2.putText(frame, "Calib Line 1", (x1 + 5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(frame, "Calib Line 2", (x2 + 5, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(frame, f"PPM: {ppm:.1f}", (10, frame_height - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Capture zone centered + offset
        capture_zone_height_px = capture_zone_height_m * ppm
        offset_px = capture_zone_offset_m * ppm
        capture_zone_top = int((frame_height - capture_zone_height_px) / 2 + offset_px)
        capture_zone_bottom = int(capture_zone_top + capture_zone_height_px)

        center_x = frame_width // 2
        horizontal_half_width_px = int(ppm * 0.5)  # ±0.5m center window

        # Draw capture zone
        cv2.rectangle(frame, (0, capture_zone_top), (frame_width, capture_zone_bottom), (255, 0, 255), 2)
        cv2.putText(frame, "Speed Capture Zone", (10, capture_zone_top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        cv2.putText(frame, f"Offset: {capture_zone_offset_m:.2f}m", (10, capture_zone_top - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        results = model.track(frame, persist=True)

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

                in_zone = capture_zone_top <= cy <= capture_zone_bottom
                in_center = (center_x - horizontal_half_width_px) <= cx <= (center_x + horizontal_half_width_px)

                data = tracker_data
                if obj_id not in data['object_history']:
                    data['object_history'][obj_id] = (cx, cy)
                    data['max_speeds'][obj_id] = 0
                    data['screenshot_taken'][obj_id] = False
                    data['screenshot_finalized'][obj_id] = False
                    data['first_seen'][obj_id] = current_time
                    data['box_cache'][obj_id] = box
                    data['speed_history'][obj_id] = []
                    data['last_time'][obj_id] = current_time
                    continue

                last_time = data['last_time'].get(obj_id, current_time)
                time_elapsed = current_time - last_time
                speed_kph, direction = compute_speed(data['object_history'][obj_id], (cx, cy), time_elapsed, ppm)
                data['object_history'][obj_id] = (cx, cy)
                data['last_time'][obj_id] = current_time
                data['last_updated'][obj_id] = current_time
                data['box_cache'][obj_id] = box
                data['max_speeds'][obj_id] = max(data['max_speeds'][obj_id], speed_kph)
                data['speed_history'][obj_id].append(speed_kph)

                label = f"{class_name} ID {obj_id} | {speed_kph:.1f} km/h"
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                if (direction == "right"
                        and speed_kph > speed_limit_kph
                        and in_zone
                        and in_center
                        and not data['screenshot_taken'][obj_id]
                        and not data['screenshot_finalized'][obj_id]):
                    path, timestamp = save_screenshot(frame, box, obj_id, class_name, speed_kph)
                    log_to_csv(timestamp, obj_id, class_name, speed_kph, path, direction)
                    data['screenshot_taken'][obj_id] = True
                    data['screenshot_finalized'][obj_id] = True

        cv2.imshow("YOLOv8 Speed Tracker", frame)
        if cv2.waitKey(1) == 27:
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLOv8 Speed Tracker")
    parser.add_argument("--video", type=str, help="Path to a video file. If not provided, webcam will be used.")
    args = parser.parse_args()

    setup_environment()
    config = load_config()
    is_live = args.video is None
    root = Tk()
    root.title("Live Calibration")
    controls = create_controls(root, config)

    model = YOLO(MODEL_PATH)
    cap = initialize_video_source(args.video)
    tracker_data = initialize_tracker()
    class_names = model.model.names

    try:
        main_loop(cap, model, controls, tracker_data, class_names, root, is_live)
    except Exception as e:
        print("🔥 Error in main loop:", e)
        traceback.print_exc()
    finally:
        try: save_config(controls)
        except: pass
        try: cap.release()
        except: pass
        try: cv2.destroyAllWindows()
        except: pass
        try: root.destroy()
        except: pass