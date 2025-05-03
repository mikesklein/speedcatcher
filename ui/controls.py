# yolo_speed_tracker/ui/controls.py
from tkinter import Scale, Label, HORIZONTAL, IntVar, DoubleVar, StringVar, BooleanVar, Frame, Button, Entry

from utils.config import save_config


def create_controls(root, config):
    controls = {}
    container = Frame(root)
    container.pack(padx=10, pady=10)

    # Helper to bind integer controls with slider and entry
    def bind_int_control(label_text, key, from_, to):
        slider_var = IntVar(master=root, value=int(config.get(key, from_)))
        entry_var = StringVar(master=root, value=str(slider_var.get()))

        def on_entry_change(*args):
            try:
                val = int(float(entry_var.get()))
                slider_var.set(val)
            except ValueError:
                pass

        entry_var.trace_add('write', on_entry_change)
        slider_var.trace_add('write', lambda *args: entry_var.set(str(slider_var.get())))

        Label(container, text=label_text).pack(pady=(10, 0))
        Scale(container, from_=from_, to=to, orient=HORIZONTAL, variable=slider_var).pack()
        Entry(container, textvariable=entry_var, width=7).pack()

        controls[key] = slider_var

    # Helper to bind float controls with two-decimal precision
    def bind_float_control(label_text, key, from_, to, resolution):
        slider_var = DoubleVar(master=root, value=float(config.get(key, from_)))
        entry_var = StringVar(master=root, value=f"{slider_var.get():.2f}")

        def on_entry_change(*args):
            try:
                val = round(float(entry_var.get()), 2)
                slider_var.set(val)
            except ValueError:
                pass

        entry_var.trace_add('write', on_entry_change)
        slider_var.trace_add('write', lambda *args: entry_var.set(f"{slider_var.get():.2f}"))

        Label(container, text=label_text).pack(pady=(10, 0))
        Scale(container, from_=from_, to=to, resolution=resolution, orient=HORIZONTAL, variable=slider_var).pack()
        Entry(container, textvariable=entry_var, width=7).pack()

        controls[key] = slider_var

    # Bind all controls
    bind_int_control("Pixels per Meter", 'pixels_per_meter', 50, 500)
    bind_int_control("Speed Limit (km/h)", 'speed_limit_kph', 1, 120)
    bind_int_control("Reference Box Offset Y", 'box_offset_y', -300, 300)
    bind_int_control("Reference Box Offset X", 'box_offset_x', -300, 300)

    bind_float_control("Calibration Line 1 X", 'calib_line1_x', 0.00, 1280.00, 0.01)
    bind_float_control("Calibration Line 2 X", 'calib_line2_x', 0.00, 1280.00, 0.01)
    bind_float_control("Real-world Distance (m)", 'real_world_distance_m', 0.01, 10.00, 0.01)

    # Speed capture zone controls (in meters)
    bind_float_control("Capture Zone Offset (m)", 'capture_zone_offset_m', -10.90, 10.0, 0.01)
    bind_float_control("Capture Zone Height (m)", 'capture_zone_height_m', 0.1, 10.0, 0.01)

    # Auto-update PPM when calibration values change
    def auto_update_ppm(*args):
        try:
            x1 = float(controls['calib_line1_x'].get())
            x2 = float(controls['calib_line2_x'].get())
            distance_m = float(controls['real_world_distance_m'].get())
            pixel_distance = abs(x2 - x1)
            if distance_m > 0:
                ppm = int(pixel_distance / distance_m)
                controls['pixels_per_meter'].set(ppm)
        except Exception:
            pass

    controls['calib_line1_x'].trace_add('write', auto_update_ppm)
    controls['calib_line2_x'].trace_add('write', auto_update_ppm)
    controls['real_world_distance_m'].trace_add('write', auto_update_ppm)

    # Manual calibration button
    def apply_calibration():
        try:
            x1 = float(controls['calib_line1_x'].get())
            x2 = float(controls['calib_line2_x'].get())
            distance_m = float(controls['real_world_distance_m'].get())
            pixel_distance = abs(x2 - x1)
            if distance_m > 0:
                ppm = int(pixel_distance / distance_m)
                controls['pixels_per_meter'].set(ppm)
        except Exception:
            pass

    Button(container, text="Set Pixels per Meter", command=apply_calibration).pack(pady=(10, 0))
    Button(container, text="Save Settings", command=lambda: save_config(controls)).pack(pady=10)

    # Pause/Play toggle
    controls['paused'] = BooleanVar(value=False)

    def toggle_pause():
        current = controls['paused'].get()
        controls['paused'].set(not current)
        pause_button.config(text="Resume" if current else "Pause")

    pause_button = Button(container, text="Pause", command=toggle_pause)
    pause_button.pack(pady=(10, 0))

    return controls


def update_control_values(controls):
    # No-op: syncing is handled by trace bindings in controls
    pass
