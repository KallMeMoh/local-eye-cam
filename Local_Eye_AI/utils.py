import os
from datetime import datetime
import cv2
import numpy as np
from config import FONT, LOG_FILE, LOG_MAX_BYTES

def log_event(message):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
    try:
        if os.path.getsize(LOG_FILE) > LOG_MAX_BYTES:
            os.replace(LOG_FILE, LOG_FILE + ".1")
    except OSError:
        pass
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as exc:
        print(f"Could not write log: {exc}")
    print(line)

def cleanup_storage(directory, max_bytes):
    if max_bytes <= 0:
        return
    try:
        paths = [os.path.join(directory, name) for name in os.listdir(directory)]
        files = sorted((p for p in paths if os.path.isfile(p)), key=os.path.getmtime)
        total = sum(os.path.getsize(p) for p in files)
        for path in files:
            if total <= max_bytes:
                break
            total -= os.path.getsize(path)
            os.remove(path)
            log_event(f"Storage full: deleted old file {os.path.basename(path)}")
    except OSError as exc:
        print(f"Storage cleanup failed: {exc}")

def parse_zone(text):
    try:
        if ";" in text:
            points = [tuple(float(v) for v in p.split(",")) for p in text.split(";") if p.strip()]
        else:
            left, top, right, bottom = (float(v) for v in text.split(","))
            points = [(left, top), (right, top), (right, bottom), (left, bottom)]
        if len(points) < 3 or any(len(p) != 2 for p in points):
            raise ValueError
        return np.clip(np.array(points, dtype=np.float32), 0.0, 1.0)
    except ValueError:
        print(f"Bad --zone value: {text!r} (watching the whole frame).")

def in_alert_zone(box, zone_pts, group="person"):
    if zone_pts is None:
        return True
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    points = [(cx, float(y2))]
    if group == "vehicle":
        points += [(cx, cy), (float(x1), float(y2)), (float(x2), float(y2))]
    return any(cv2.pointPolygonTest(zone_pts, p, False) >= 0 for p in points)

def th(value, k):
    return max(1, int(round(value * k)))

def put_text(frame, text, org, scale, color, thick):
    cv2.putText(frame, text, org, FONT, scale, (0, 0, 0), thick + 2, cv2.LINE_AA)
    cv2.putText(frame, text, org, FONT, scale, color, thick, cv2.LINE_AA)
