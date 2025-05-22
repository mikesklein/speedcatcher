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
from ui.controls import create_controls # update_control_values is removed as it's not used
from utils.config import DEFAULT_CONFIG # To access keys if needed
from utils.core_processing import process_detected_object
from utils.constants import (
    GUI_PHOTO_ZONE_COLOR, GUI_PHOTO_ZONE_TEXT_COLOR, GUI_REF_BOX_COLOR,
    GUI_REF_BOX_TEXT_COLOR, GUI_GROUND_LINE_COLOR, GUI_GROUND_LINE_TEXT_COLOR,
    FONT_HERSHEY_SIMPLEX, FONT_SCALE_SMALL, LINE_THICKNESS_DEFAULT,
    CENTER_TOLERANCE_METERS
)


# Helper Functions (similar to speedcatcher.py but adapted for GUI)

def update_settings_from_controls(controls, base_config):
    updated_config = base_config.copy()
    
    control_mapped_keys = [
        'pixels_per_meter', 'speed_limit_kph', 
        'box_offset_y', 'box_offset_x',
        'calib_line1_x', 'calib_line2_x', 'real_world_distance_m',
        'capture_zone_offset_m', 'capture_zone_height_m',
        'zone_size_m'
    ]
    
    for key in control_mapped_keys:
        if key in controls and controls[key] is not None: # Check if control exists and is not None
            try:
                updated_config[key] = controls[key].get()
            except Exception as e:
                print(f"Warning: Could not get value for control {key}: {e}")
        elif key not in updated_config: # Ensure key exists from base_config or default
             updated_config[key] = DEFAULT_CONFIG.get(key)


    if 'box_scale' in controls and controls['box_scale'] is not None:
        updated_config['box_scale_factor'] = controls['box_scale'].get() / 100.0
    elif 'box_scale_factor' not in updated_config : # Ensure key exists
        updated_config['box_scale_factor'] = DEFAULT_CONFIG.get('box_scale_factor',1.0)


    # Ensure essential keys are present, falling back to DEFAULT_CONFIG if not in base_config
    if 'allowed_classes' not in updated_config:
        updated_config['allowed_classes'] = DEFAULT_CONFIG['allowed_classes']
    if 'model_path' not in updated_config:
        updated_config['model_path'] = DEFAULT_CONFIG['model_path']
    
    return updated_config

def draw_gui_overlays(frame, config):
    frame_height, frame_width = frame.shape[:2]
    
    ppm = config.get('pixels_per_meter', 100)
    zone_size_m = config.get('zone_size_m', 5.0)
    offset_x = config.get('box_offset_x', 0)
    offset_y = config.get('box_offset_y', 0)
    scale_factor = config.get('box_scale_factor', 1.0)
    
    center_x_ref = frame_width // 2
    center_y_ref = (frame_height // 2) - 100 

    zone_pixels = int(ppm * zone_size_m)
    zone_left = max(center_x_ref - zone_pixels // 2, 0)
    zone_right = min(center_x_ref + zone_pixels // 2, frame_width)
    zone_top = max(center_y_ref - zone_pixels // 2, 0)
    zone_bottom = min(center_y_ref + zone_pixels // 2, frame_height)
    cv2.rectangle(frame, (zone_left, zone_top), (zone_right, zone_bottom), GUI_PHOTO_ZONE_COLOR, LINE_THICKNESS_DEFAULT)
    cv2.putText(frame, "Photo Zone", (zone_left, zone_top - 10), FONT_HERSHEY_SIMPLEX, FONT_SCALE_SMALL, GUI_PHOTO_ZONE_TEXT_COLOR, LINE_THICKNESS_DEFAULT)

    box_center_x_final = center_x_ref + offset_x
    box_center_y_final = center_y_ref + offset_y
    box_size_pixels = int(ppm * scale_factor)

    box_top_left = (box_center_x_final - box_size_pixels // 2, box_center_y_final - box_size_pixels // 2)
    box_bottom_right = (box_center_x_final + box_size_pixels // 2, box_center_y_final + box_size_pixels // 2)
    cv2.rectangle(frame, box_top_left, box_bottom_right, GUI_REF_BOX_COLOR, LINE_THICKNESS_DEFAULT)
    cv2.putText(frame, "1 meter reference", (box_top_left[0], box_top_left[1] - 10), FONT_HERSHEY_SIMPLEX, FONT_SCALE_SMALL, GUI_REF_BOX_TEXT_COLOR, LINE_THICKNESS_DEFAULT)

    _center_y_for_gy = (frame_height // 2) - 100
    _box_size_for_gy = int(ppm * scale_factor)
    gy = _center_y_for_gy + offset_y + (_box_size_for_gy // 2) + int(ppm * config.get('ground_line_distance_m', 1.0)) # Using a configurable distance

    cv2.line(frame, (0, gy), (frame_width, gy), GUI_GROUND_LINE_COLOR, LINE_THICKNESS_DEFAULT)
    cv2.putText(frame, "Ground Line (Calibrated)", (10, gy - 10), FONT_HERSHEY_SIMPLEX, FONT_SCALE_SMALL, GUI_GROUND_LINE_TEXT_COLOR, LINE_THICKNESS_DEFAULT)

    zone_center_x_calc = (zone_left + zone_right) // 2
    zone_center_y_calc = (zone_top + zone_bottom) // 2
    center_tolerance_calc = int(ppm * CENTER_TOLERANCE_METERS)
    
    return zone_center_x_calc, zone_center_y_calc, center_tolerance_calc

# process_gui_object function is now removed and imported from utils.core_processing


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLOv8 Speed Tracker GUI")
    parser.add_argument("--video", type=str, help="Path to a video file. If not provided, webcam will be used.")
    args = parser.parse_args()

    setup_environment()
    source = args.video if args.video else 0
    
    initial_config = load_config() 

    root = Tk()
    root.title("Live Calibration & Speed Tracker")

    controls = create_controls(root, initial_config) # Pass initial_config to populate controls
    
    model = YOLO(initial_config['model_path']) # Load model using path from config
    
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: Could not open video source: {source}")
        exit()
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = 30 if fps is None or fps <= 0 else fps

    tracker_data = initialize_tracker()
    class_names = model.model.names
    
    # For pause functionality
    if 'paused' not in controls: # Ensure pause control exists
        controls['paused'] = IntVar(value=0) # Add a dummy one if not created by create_controls

    try:
        while True:
            root.update_idletasks()
            root.update()

            if controls['paused'].get() == 1:
                time.sleep(0.01) 
                # Display the last processed frame or a pause message if frame is None
                # This requires storing the last frame. For now, just sleeps.
                # If frame is available, can do: cv2.imshow("YOLOv8 Speed Tracker", last_frame_with_pause_text)
                # And then continue the loop without reading a new frame.
                # This part needs careful handling of frame display when paused.
                # A simple approach is to just not update the frame if paused after the first display.
                # The current loop structure will re-display the *current* frame if paused.
                # For true pause of display, frame processing must be conditional.
                # Let's assume for now that if paused, we skip reading and processing new frames.
                # This means we need to show the frame *before* the pause check or store the last frame.
                # For simplicity, let's just process if not paused.

                # A better pause:
                # Read frame before pause check. If paused, display it and loop.
                # This is not what the provided logic sketch does.
                # The sketch has pause check, then read frame.
                # Let's stick to the sketch: if paused, it just skips.
                # The frame shown will be the *last* one before pause from previous iteration.
                continue


            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame or video ended.")
                break
            
            current_time = time.time()
            
            current_frame_config = update_settings_from_controls(controls, initial_config.copy())
            
            zone_center_x, zone_center_y, center_tolerance = draw_gui_overlays(frame, current_frame_config)
            
            results = model.track(frame, persist=True, verbose=False)

            if results[0].boxes is not None and results[0].boxes.id is not None:
                ids = results[0].boxes.id.cpu().numpy()
                boxes = results[0].boxes.xyxy.cpu().numpy()
                class_ids = results[0].boxes.cls.cpu().numpy()

                for obj_id, box, cls_id in zip(ids, boxes, class_ids):
                process_detected_object( # Renamed function call
                        obj_id, box, cls_id, class_names, tracker_data, 
                        current_time, frame, current_frame_config, fps, 
                        zone_center_x, zone_center_y, center_tolerance
                    )
            
            cv2.imshow("YOLOv8 Speed Tracker", frame)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC key
                break
    except Exception as e:
        print(f"An error occurred in the main loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'controls' in locals() and controls: # Ensure controls exist
             save_config(controls) 
        
        if 'cap' in locals() and cap: cap.release()
        cv2.destroyAllWindows()
        if 'root' in locals() and root: root.destroy()
