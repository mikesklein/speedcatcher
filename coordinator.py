import os
import subprocess
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

CAPTURE_DIR = Path("captures")
PROCESSED_LOG = Path("processed_files.txt")
LOCK_EXT = ".lock"
CAPTURE_SCRIPT = "capture.py"
PROCESS_SCRIPT = "main.py"
MAX_WORKERS = 2
CHECK_INTERVAL = 5  # seconds

def start_capture():
    print("🎥 Starting capture.py...")
    return subprocess.Popen(["python", CAPTURE_SCRIPT])

def get_processed_files():
    if PROCESSED_LOG.exists():
        return set(PROCESSED_LOG.read_text().splitlines())
    return set()

def mark_as_processed(filename):
    with PROCESSED_LOG.open("a") as f:
        f.write(f"{filename}\n")

def lock_file(file):
    lock_path = file.with_suffix(file.suffix + LOCK_EXT)
    try:
        lock_path.touch(exist_ok=False)
        return lock_path
    except FileExistsError:
        return None

def unlock_file(lock_path):
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass

def is_file_ready(file):
    return file.exists()

def process_file(file):
    lock_path = lock_file(file)
    if not lock_path:
        return

    try:
        print(f"🧠 Processing: {file}")
        subprocess.run(["python", PROCESS_SCRIPT, "--video", str(file)], check=True)
        mark_as_processed(file.name)
        print(f"✅ Done: {file.name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to process {file.name}: {e}")
    finally:
        unlock_file(lock_path)

def monitor_directory():
    processed = get_processed_files()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while True:
            files_to_process = [f for f in sorted(CAPTURE_DIR.glob("*.avi")) if f.name not in processed and is_file_ready(f)]
            if not files_to_process:
                print("📭 No new files found. Monitoring complete.")
                break

            for file in files_to_process:
                executor.submit(process_file, file)
                processed.add(file.name)

            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    CAPTURE_DIR.mkdir(exist_ok=True)
    PROCESSED_LOG.touch(exist_ok=True)

    capture_proc = start_capture()
    print("⏳ Waiting for capture to complete...")
    capture_proc.wait()
    print("📦 Capture finished. Starting processing phase...")
    monitor_directory()