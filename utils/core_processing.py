import cv2
from utils.tracking import compute_speed, save_screenshot, log_to_csv
from .constants import FONT_HERSHEY_SIMPLEX, LABEL_FONT_SCALE, LABEL_FONT_THICKNESS, LABEL_TEXT_COLOR, LABEL_BG_COLOR

# Definition of process_detected_object (copied from process_object)
def process_detected_object(obj_id, box, cls_id, class_names, tracker_data, current_time, frame, config, fps, zone_center_x, zone_center_y, center_tolerance):
    # Ensure all necessary keys are accessed from the config dictionary
    # config keys used: 'allowed_classes', 'pixels_per_meter', 'speed_limit_kph'

    if int(cls_id) not in config['allowed_classes']:
        return

    x1, y1, x2, y2 = map(int, box)
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    center = (cx, cy)
    class_name = class_names[int(cls_id)]

    if obj_id not in tracker_data['object_history']:
        tracker_data['object_history'][obj_id] = center
        tracker_data['max_speeds'][obj_id] = 0
        tracker_data['screenshot_taken'][obj_id] = False
        tracker_data['screenshot_finalized'][obj_id] = False
        tracker_data['first_seen'][obj_id] = current_time
        tracker_data['box_cache'][obj_id] = box # Store the initial box
        tracker_data['speed_history'][obj_id] = []
        return

    prev_center = tracker_data['object_history'][obj_id]
    
    # Ensure pixels_per_meter is correctly passed and used
    pixels_per_meter_val = config.get('pixels_per_meter', 100) # Default if not in config
    speed_kph, _ = compute_speed(prev_center, center, fps, pixels_per_meter_val)

    tracker_data['object_history'][obj_id] = center
    tracker_data['last_updated'][obj_id] = current_time
    tracker_data['box_cache'][obj_id] = box # Update box for potential future screenshot

    if speed_kph <= config['speed_limit_kph']:
        return

    tracker_data['max_speeds'][obj_id] = max(tracker_data['max_speeds'][obj_id], speed_kph)
    tracker_data['speed_history'][obj_id].append(speed_kph)

    label = f"{class_name} ID {obj_id} | Now: {speed_kph:.1f} km/h"
    font = FONT_HERSHEY_SIMPLEX # Use the constant for font type
    scale = LABEL_FONT_SCALE
    thickness = LABEL_FONT_THICKNESS
    (text_width, text_height), _ = cv2.getTextSize(label, font, scale, thickness)
    
    label_x, label_y = x1, y1 - 10
    if label_y - text_height < 0:
        label_y = y1 + text_height + 10
    
    cv2.rectangle(frame, (label_x, label_y - text_height - 4), (label_x + text_width + 6, label_y + 4), LABEL_BG_COLOR, -1)
    cv2.putText(frame, label, (label_x, label_y), font, scale, LABEL_TEXT_COLOR, thickness)

    at_center = (
        abs(cx - zone_center_x) <= center_tolerance and
        abs(cy - zone_center_y) <= center_tolerance
    )

    if speed_kph > config['speed_limit_kph'] and at_center and \
       not tracker_data['screenshot_taken'][obj_id] and \
       not tracker_data['screenshot_finalized'][obj_id]:
        
        # save_screenshot and log_to_csv are from utils.tracking
        screenshot_path, timestamp = save_screenshot(frame, box, obj_id, class_name, speed_kph)
        log_to_csv(timestamp, obj_id, class_name, speed_kph, screenshot_path)
        
        tracker_data['screenshot_taken'][obj_id] = True
        tracker_data['screenshot_finalized'][obj_id] = True
