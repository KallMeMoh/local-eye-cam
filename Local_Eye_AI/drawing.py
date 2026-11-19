import time
import cv2
import numpy as np
import state
from config import (CLOSE_BTN, EXIT_BTN, FONT, HEIGHT, MIRROR_BTN, OPEN_BTN, ORANGE, PREVIEW_HEIGHT,RED, REC_NO_BTN, REC_YES_BTN, VIEW_TOP, WHITE, WIDTH)
from utils import put_text, th

def draw_object_zone(frame, box, confirmed, k):
    x1, y1, x2, y2 = box
    h, w = frame.shape[:2]
    pad = int(14 * k)
    zx1, zy1, zx2, zy2 = max(0, x1 - pad), max(0, y1 - pad), min(w - 1, x2 + pad), min(h - 1, y2 + pad)
    if not confirmed:
        cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), ORANGE, th(1.5, k))
        return
    cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), RED, th(2.5, k))
    corner = max(int(min(zx2 - zx1, zy2 - zy1) * 0.22), int(12 * k))
    for px, py, dx, dy in ((zx1, zy1, 1, 1), (zx2, zy1, -1, 1), (zx1, zy2, 1, -1), (zx2, zy2, -1, -1)):
        cv2.line(frame, (px, py), (px + dx * corner, py), RED, th(4, k))
        cv2.line(frame, (px, py), (px, py + dy * corner), RED, th(4, k))

def draw_alerts(frame, texts, k):
    if not texts:
        return
    margin, gap, height = int(10 * k), int(8 * k), int(34 * k)
    rad = height // 2
    scale, thick = 0.55 * k, th(1.5, k)
    badges, y = [], margin
    for text in texts:
        text_w, text_h = cv2.getTextSize(text, FONT, scale, thick)[0]
        x1 = frame.shape[1] - margin - (rad * 3 + text_w)
        badges.append((x1, y, frame.shape[1] - margin, text, text_h))
        y += height + gap
    overlay = frame.copy()
    for x1, y1, x2, _, _ in badges:
        cv2.rectangle(overlay, (x1 + rad, y1), (x2 - rad, y1 + height), (0, 0, 170), -1)
        for cx in (x1 + rad, x2 - rad):
            cv2.circle(overlay, (cx, y1 + rad), rad, (0, 0, 170), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    icon_color = WHITE if int(time.monotonic() * 2) % 2 == 0 else (200, 200, 255)
    mark_w, mark_h = cv2.getTextSize("!", FONT, 0.6 * k, th(2, k))[0]
    for x1, y1, _, text, text_h in badges:
        cx, cy = x1 + rad, y1 + rad
        cv2.circle(frame, (cx, cy), max(rad - th(5, k), 4), icon_color, -1)
        cv2.putText(frame, "!", (cx - mark_w // 2, cy + mark_h // 2), FONT, 0.6 * k, (0, 0, 200), th(2, k))
        cv2.putText(frame, text, (x1 + rad * 2, cy + text_h // 2), FONT, scale, WHITE, thick)

def draw_zone(frame, k):
    h, w = frame.shape[:2]
    points = np.round(state.zone_poly * np.array([w, h], dtype=np.float32)).astype(np.int32)
    inset = th(2, k)
    visible = np.stack([np.clip(points[:, 0], inset, w - 1 - inset),
                        np.clip(points[:, 1], inset, h - 1 - inset)], axis=1)
    cv2.polylines(frame, [visible], True, RED, th(1.5, k))
    return points

def draw_button(image, bounds, text, color):
    x1, y1, x2, y2 = bounds
    cv2.rectangle(image, (x1, y1), (x2, y2), color, -1)
    cv2.rectangle(image, (x1, y1), (x2, y2), WHITE, 2)
    width, height = cv2.getTextSize(text, FONT, 0.7, 2)[0]
    origin = (x1 + (x2 - x1 - width) // 2, y1 + (y2 - y1 + height) // 2)
    cv2.putText(image, text, origin, FONT, 0.7, WHITE, 2, cv2.LINE_AA)

def make_view(frame):
    h, w = frame.shape[:2]
    scale = min(WIDTH / w, PREVIEW_HEIGHT / h)
    return cv2.resize(frame, (int(w * scale), int(h * scale)))

def render_window(view, fps, frame_size):
    cam, app_bridge = state.cam, state.app_bridge
    display = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    if cam is None:
        cv2.putText(display, "SMART CAMERA AI", (250, 200), FONT, 1.2, WHITE, 2)
        cv2.putText(display, "Camera is OFF", (330, 280), FONT, 0.9, RED, 2)
    else:
        if view is not None:
            vh, vw = view.shape[:2]
            y0, x0 = VIEW_TOP + (PREVIEW_HEIGHT - vh) // 2, (WIDTH - vw) // 2
            display[y0:y0 + vh, x0:x0 + vw] = view
            cv2.putText(display, f"{fps:.1f} FPS", (WIDTH - 120, 514), FONT, 0.5, (0, 255, 255), 1)
            if frame_size:
                cv2.putText(display, f"{frame_size[0]}x{frame_size[1]}", (20, 514), FONT, 0.5, (200, 200, 200), 1)
        if not cam.connected:
            cv2.putText(display, "Reconnecting...", (330, 250), FONT, 0.9, ORANGE, 2)
        if app_bridge.pending is not None:
            put_text(display, "ALERT - record this event?", (270, 445), 0.7, WHITE, 2)
            draw_button(display, REC_YES_BTN, "Record (R)", (30, 30, 180))
            draw_button(display, REC_NO_BTN, "Ignore (N)", (100, 100, 100))
    cv2.putText(display, f"Rec mode: {app_bridge.mode.upper()} (A)", (WIDTH // 2 - 80, 514), FONT, 0.5, (255, 255, 0), 1)
    draw_button(display, OPEN_BTN, "Open Camera", (30, 140, 30))
    draw_button(display, CLOSE_BTN, "Close Camera", (30, 30, 180))
    draw_button(display, MIRROR_BTN, f"Mirror: {'ON' if state.mirror_on else 'OFF'}",
                (160, 100, 30) if state.mirror_on else (100, 100, 100))
    draw_button(display, EXIT_BTN, "Exit", (100, 100, 100))
    return display
