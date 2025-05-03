# SpeedCatcher 🚗💨

SpeedCatcher is a Python-based speed detection system using the YOLOv8 object detection model. It tracks vehicles in real-time from a webcam or video file, estimates their speed based on pixel distance and calibration lines, and captures screenshots of speeding vehicles. All data is logged and visualized in a live dashboard.

---

## 🔧 Features

- Object detection and tracking using YOLOv8
- Real-time speed estimation in km/h
- Calibration via two horizontal reference lines and real-world distance input
- Adjustable detection zone and speed threshold
- Automatic screenshot capture of speeding vehicles
- CSV-based logging of each event
- Interactive control panel with sliders and pause/resume
- Live dashboard with plots and statistics

---

## 📂 Project Structure

```
SpeedCatcher/
├── main.py              # Main app for detection and tracking
├── dashboard.py         # Dashboard for data visualization
├── ui/
│   └── controls.py      # UI controls for calibration and settings
├── utils/
│   ├── config.py        # Load/save settings
│   ├── environment.py   # Setup folders
│   └── tracking.py      # Object tracking and logging logic
├── calibration.json     # Saved UI settings
├── speed_log.csv        # Automatically created data log
├── screenshots/         # Automatically saved screenshots
└── .gitignore
```

---

## 🧠 Requirements

- Python 3.9+
- [ultralytics](https://github.com/ultralytics/ultralytics)
- OpenCV
- Pandas
- Matplotlib
- Tkinter (usually included with Python)

Install dependencies:
```bash
pip install ultralytics opencv-python pandas matplotlib
```
