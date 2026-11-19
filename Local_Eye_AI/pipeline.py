
import time
import cv2
import state
from config import (ALERT_GROUPS, CLASS_GROUPS, GROUP_COLOR, ORANGE, PREVIEW_HEIGHT, RED, STALE_AFTER, UNATTENDED_GROUPS, WHITE, WIDTH)
from detection import (check_unattended, detect_objects, evaluate_object_zone, object_info, update_fire)
from drawing import draw_alerts, draw_object_zone, draw_zone
from utils import in_alert_zone, put_text, th

def process_frame(raw):
    h, w = raw.shape[:2]
    k = max(w / WIDTH, h / PREVIEW_HEIGHT)
    now = time.monotonic()
    app_bridge = state.app_bridge
    detections = detect_objects(raw, now)
    fire, fire_just_fired = update_fire(raw, now)
    vis = raw.copy()
    zone_pts = draw_zone(vis, k) if state.zone_poly is not None else None
    person_boxes = [d["box"] for d in detections if d["group"] == "person"]
    counts = {group: 0 for group in CLASS_GROUPS}
    confirmed_objects, newly_triggered, confirmed_names = [], [], []
    unattended = False
    for det in detections:
        group, track = det["group"], det["state"]
        x1, y1, x2, y2 = det["box"]
        color = GROUP_COLOR[group]
        label = f"ID:{det['id']} {det['name']} {det['conf']:.0%}"
        counts[group] += 1
        state.seen_ids[group].add(det["id"])
        if group in ALERT_GROUPS:
            if in_alert_zone(det["box"], zone_pts, group):
                confirmed, just_triggered, label = evaluate_object_zone(det, label, now)
                draw_object_zone(vis, det["box"], confirmed, k)
                color = RED if confirmed else ORANGE
                if confirmed:
                    confirmed_names.append(det["name"])
                    info = object_info(det)
                    confirmed_objects.append(info)
                    if just_triggered:
                        newly_triggered.append(info)
            else:
                track["zone_start"], track["alert_sent"] = None, False
        if group in UNATTENDED_GROUPS:
            was_alerted = track["unattended_alerted"]
            left_alone, label = check_unattended(det, label, person_boxes, w, now)
            if left_alone:
                color, unattended = RED, True
                info = object_info(det, reason="unattended")
                confirmed_objects.append(info)
                if not was_alerted and track["unattended_alerted"]:
                    newly_triggered.append(info)
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, th(2, k))
        put_text(vis, label, (x1, max(y1 - int(18 * k), int(22 * k))), 0.5 * k, color, th(1.5, k))
    for track_id in [t for t, s in state.tracks.items() if now - s["last"] > STALE_AFTER]:
        del state.tracks[track_id]
    for x1, y1, x2, y2, text in state.fire_state["boxes"]:
        cv2.rectangle(vis, (x1, y1), (x2, y2), RED, th(3, k))
        put_text(vis, text, (x1, max(y1 - int(10 * k), int(20 * k))), 0.6 * k, RED, th(1.5, k))
    if fire:
        fire_info = {"id": 0, "type": "fire_or_smoke", "group": "fire"}
        confirmed_objects.append(fire_info)
        if fire_just_fired:
            newly_triggered.append(fire_info)
    if confirmed_objects:
        app_bridge.notify_confirmed_objects(confirmed_objects, newly_triggered, raw, vis)
    summary = "  ".join(f"{g}: {counts[g]}/{len(state.seen_ids[g])}" for g in CLASS_GROUPS if state.seen_ids[g])
    put_text(vis, summary or "Monitoring...", (int(12 * k), int(28 * k)), 0.55 * k, WHITE, th(1.5, k))
    alerts = []
    if app_bridge.is_recording:
        alerts.append("REC - Recording")
    elif app_bridge.pending is not None:
        alerts.append("Waiting for admin: record?")
    if fire:
        alerts.append("Fire / Smoke")
    if unattended:
        alerts.append("Unattended bag")
    if confirmed_names:
        alerts.append("ALERT: " + ", ".join(sorted(set(confirmed_names))).capitalize())
    draw_alerts(vis, alerts, k)
    app_bridge.update(vis if state.args.record_overlay else raw)
    return vis
