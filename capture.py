import cv2
import os
import time
from datetime import datetime
import subprocess
import threading

# --- Configuration ---
CAMERA_INDEX = 0
FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080
FPS = 30
CHUNK_DURATION_MINUTES = 1
CHUNK_DURATION_SECONDS = CHUNK_DURATION_MINUTES * 60
TOTAL_DURATION_SECONDS = 60 * 60  # Run for 1 hour
OUTPUT_DIR = "captures"

# --- Setup ---
os.makedirs(OUTPUT_DIR, exist_ok=True)
cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

if not cap.isOpened():
    print("❌ Failed to open camera.")
    exit(1)

fourcc = cv2.VideoWriter_fourcc(*"MJPG")
chunk_index = 1
start_time = time.time()
session_start_time = start_time

def new_writer(chunk_index):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capture_{chunk_index:03d}_{timestamp}.avi"
    path = os.path.join(OUTPUT_DIR, filename)
    print(f"📹 Starting new recording: {path}")
    writer = cv2.VideoWriter(path, fourcc, FPS, (FRAME_WIDTH, FRAME_HEIGHT))
    return writer, path

def convert_avi_to_mov_and_delete(avi_path):
    base, _ = os.path.splitext(avi_path)
    mov_path = base + ".mov"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", avi_path,
        "-vcodec", "prores_ks",
        "-pix_fmt", "yuv422p10le",
        mov_path
    ]
    print(f"🎞️ Converting {avi_path} → {mov_path}")
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        os.remove(avi_path)
        print(f"🗑️ Deleted original: {avi_path}")
    except subprocess.CalledProcessError:
        print(f"❌ Failed to convert {avi_path}")

# --- Start First Chunk ---
out, current_avi_path = new_writer(chunk_index)

# --- Recording Loop ---
try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Failed to read frame.")
            break

        # Draw timestamp in upper-right
        timestamp_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        (text_width, _), _ = cv2.getTextSize(timestamp_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.putText(
            frame,
            timestamp_text,
            (FRAME_WIDTH - text_width - 10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        out.write(frame)
        cv2.imshow("Live Capture", frame)

        if cv2.waitKey(1) == 27:  # ESC key to stop
            print("⏹️ ESC pressed. Stopping capture.")
            break

        # Chunk duration check
        if time.time() - start_time >= CHUNK_DURATION_SECONDS:
            out.release()

            # Background conversion
            threading.Thread(
                target=convert_avi_to_mov_and_delete,
                args=(current_avi_path,),
                daemon=True
            ).start()

            chunk_index += 1
            out, current_avi_path = new_writer(chunk_index)
            start_time = time.time()

        # Total session time check
        if time.time() - session_start_time >= TOTAL_DURATION_SECONDS:
            print("⏳ One hour limit reached. Stopping capture.")
            break

except KeyboardInterrupt:
    print("\n⏹️ Capture interrupted by user.")

finally:
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("✅ Capture finished.")