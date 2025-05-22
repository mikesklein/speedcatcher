# utils/constants.py

# Colors (B, G, R)
COLOR_BLUE = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (0, 0, 255)
COLOR_YELLOW = (0, 255, 255)
COLOR_CYAN = (255, 255, 0) # Used for ground line in original speedcatcher
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)

# Font Properties
FONT_HERSHEY_SIMPLEX = 0 # cv2.FONT_HERSHEY_SIMPLEX is 0
FONT_SCALE_SMALL = 0.6
FONT_SCALE_MEDIUM = 0.8
FONT_THICKNESS_DEFAULT = 2

# Drawing Parameters
LINE_THICKNESS_DEFAULT = 2
RECTANGLE_THICKNESS_DEFAULT = 2

# Object Label Properties
LABEL_FONT_SCALE = 0.6
LABEL_FONT_THICKNESS = 2
LABEL_BG_COLOR = COLOR_BLACK
LABEL_TEXT_COLOR = COLOR_YELLOW # Original label color in speedcatcher.py

# Reference Overlay Properties (speedcatcher.py specific, if not from config)
# These are fixed visual cues. Configurable ones are in config.
CENTER_LINE_COLOR = COLOR_BLUE
REFERENCE_BOX_COLOR = COLOR_GREEN
REFERENCE_BOX_TEXT_COLOR = COLOR_GREEN
GROUND_LINE_COLOR_SC = COLOR_CYAN # SC for speedcatcher.py
PHOTO_ZONE_COLOR = COLOR_RED
PHOTO_ZONE_TEXT_COLOR = COLOR_RED # For "Photo Zone" text

# GUI Overlay Properties (speedcatcher_gui.py specific, if not from config)
GUI_PHOTO_ZONE_COLOR = COLOR_RED # Same as above, but good to distinguish if they diverge
GUI_PHOTO_ZONE_TEXT_COLOR = COLOR_WHITE # GUI uses white for this text
GUI_REF_BOX_COLOR = COLOR_GREEN
GUI_REF_BOX_TEXT_COLOR = COLOR_WHITE # GUI uses white
GUI_GROUND_LINE_COLOR = COLOR_YELLOW # GUI uses yellow
GUI_GROUND_LINE_TEXT_COLOR = COLOR_WHITE # GUI uses white

# Other constants if identified
# Example: JITTER_THRESHOLD_PIXELS was added to utils.tracking.py. That's a good place for it.
# The 0.5 meter margin for center_tolerance could be a constant.
CENTER_TOLERANCE_METERS = 0.5 # Currently hardcoded as 0.5 in draw_reference_overlays and draw_gui_overlays
# This is used as: int(pixels_per_meter * CENTER_TOLERANCE_METERS)
