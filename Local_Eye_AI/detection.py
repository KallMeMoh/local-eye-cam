import numpy as np
import state
from config import (CONFIRM_SECONDS, FIRE_CONFIRM, FIRE_COOLDOWN, GROUP_CONF, MIN_BOX_RATIO,MIN_FRAMES, MOVE_TOLERANCE, NAME_TO_GROUP, NMS_IOU, TRACK_CONF,UNATTENDED_AFTER, ZONE_GRACE)
from utils import log_event

def new_track(name, group):
    return {"name": name, "group": group, "frames": 0, "last": 0.0, "zone_start": None, "zone_last_in": 0.0,
            "alert_sent": False, "anchor": None, "owner_seen": 0.0, "unattended_alerted": False}
def reset_tracking():
    state.tracks.clear()
    for ids in state.seen_ids.values():
        ids.clear()
    state.fire_state.update(boxes=[], hits=0, last_alert=0.0, frame_no=0)
    predictor = getattr(state.model, "predictor", None)
    for tracker in getattr(predictor, "trackers", []):
        tracker.reset()
def person_near(box, person_boxes):
    cx, cy = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
    for px1, py1, px2, py2 in person_boxes:
        margin = 0.25 * max(px2 - px1, py2 - py1)
        if px1 - margin <= cx <= px2 + margin and py1 - margin <= cy <= py2 + margin:
            return True
    return False
def object_info(det, **extra):
    return {"id": det["id"], "type": det["name"], "group": det["group"], "conf": round(det["conf"], 2), **extra}
def detect_objects(frame, now):
    args = state.args
    result = state.model.track(frame, persist=True, tracker="bytetrack.yaml", conf=TRACK_CONF, iou=NMS_IOU,classes=state.target_class_ids, imgsz=args.imgsz, device=args.device,verbose=False)[0]
    detections = []
    if result.boxes is None:
        return detections
    min_area = MIN_BOX_RATIO * frame.shape[0] * frame.shape[1]
    for box in result.boxes:
        if box.id is None:
            continue
        name = result.names[int(box.cls[0])]
        group, conf = NAME_TO_GROUP.get(name), float(box.conf[0])
        if group is None or conf < GROUP_CONF[group]:
            continue
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        if (x2 - x1) * (y2 - y1) < min_area:
            continue
        track_id = int(box.id[0])
        track = state.tracks.setdefault(track_id, new_track(name, group))
        track["frames"] += 1
        track["last"] = now
        if track["frames"] >= MIN_FRAMES:
            detections.append({"id": track_id, "name": name, "group": group, "conf": conf,"box": (x1, y1, x2, y2), "state": track})
    return detections
def evaluate_object_zone(det, label, now):
    track = det["state"]
    if track["zone_start"] is not None and now - track["zone_last_in"] > ZONE_GRACE:
        track["zone_start"], track["alert_sent"] = None, False
    track["zone_last_in"] = now
    if track["zone_start"] is None:
        track["zone_start"] = now
    elapsed = now - track["zone_start"]
    if elapsed < CONFIRM_SECONDS:
        return False, False, f"{label} | Locking: {elapsed:.1f}s"
    just_triggered = not track["alert_sent"]
    if just_triggered:
        track["alert_sent"] = True
        log_event(f"ALERT: {det['name']} (ID {det['id']}) stayed > {CONFIRM_SECONDS}s -> Locked & Triggered!")
    return True, just_triggered, f"{label} | ALERT ({elapsed:.1f}s)"
def check_unattended(det, label, person_boxes, frame_width, now):
    track = det["state"]
    x1, y1, x2, y2 = det["box"]
    center, anchor = ((x1 + x2) / 2, (y1 + y2) / 2), track["anchor"]
    if anchor is None or np.hypot(center[0] - anchor[0], center[1] - anchor[1]) > MOVE_TOLERANCE * frame_width:
        track.update(anchor=center, owner_seen=now, unattended_alerted=False)
    if person_near(det["box"], person_boxes):
        track["owner_seen"] = now
    alone = now - track["owner_seen"]
    if alone >= 3:
        label += f" | Alone: {alone:.0f}s"
    if alone >= UNATTENDED_AFTER and not track["unattended_alerted"]:
        track["unattended_alerted"] = True
        log_event(f"ALERT: Unattended {det['name']} (ID {det['id']}) for {alone:.0f}s.")
    return alone >= UNATTENDED_AFTER, label

def update_fire(frame, now):
    fire_model, args, fire_state = state.fire_model, state.args, state.fire_state
    if fire_model is None:
        return False, False
    fire_state["frame_no"] += 1
    if args.fire_every == 1 or fire_state["frame_no"] % args.fire_every == 1:
        result = fire_model.predict(frame, conf=args.fire_conf, imgsz=args.imgsz,
                                    device=args.device, verbose=False)[0]
        boxes = []
        for box in (result.boxes or []):
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            boxes.append((x1, y1, x2, y2, f"{result.names[int(box.cls[0])]} {float(box.conf[0]):.0%}"))
        fire_state["boxes"] = boxes
        fire_state["hits"] = fire_state["hits"] + 1 if boxes else 0
    confirmed = fire_state["hits"] >= FIRE_CONFIRM
    just_fired = confirmed and now - fire_state["last_alert"] > FIRE_COOLDOWN
    if just_fired:
        fire_state["last_alert"] = now
        log_event("ALERT: Fire or smoke detected!")
    return confirmed, just_fired
