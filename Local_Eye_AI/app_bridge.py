import json
import os
import time
from collections import deque
from datetime import datetime
import cv2
from utils import cleanup_storage, log_event

class AppBridgeController:
    MODES = ("auto", "ask")
    DISMISS_QUIET_SEC = 15.0
    URGENT_GROUPS = ("fire", "danger")
    WRITER_RETRY_SEC = 60.0
    CODECS = (("mp4", "avc1"), ("mp4", "mp4v"), ("avi", "MJPG"))

    def __init__(self, save_dir, command_file, reply_file, post_roll_sec=10.0, pre_roll_sec=2.0, max_clip_sec=120.0, video_fps=20.0, mode="auto", ask_timeout_sec=45.0,max_buffer_sec=15.0, jpeg_quality=65, max_storage_bytes=0):
        self.save_dir, self.command_file, self.reply_file = save_dir, command_file, reply_file
        self.post_roll_sec, self.pre_roll_sec = post_roll_sec, pre_roll_sec
        self.max_clip_sec, self.video_fps = max_clip_sec, float(video_fps)
        self.mode = mode if mode in self.MODES else "auto"
        self.ask_timeout_sec, self.max_buffer_sec = ask_timeout_sec, max_buffer_sec
        self.jpeg_quality, self.max_storage_bytes = jpeg_quality, max_storage_bytes
        self.writer, self.current_video_path = None, None
        self.writer_ok, self.writer_failed_at = True, 0.0
        self.size = self.last_size = self.t0 = None
        self.frames_out = 0
        self.buffer = deque()
        self.is_recording = False
        self.last_confirmed_time, self.started, self.quiet_until = -1e9, 0.0, 0.0
        self.seq = self.alert_id = 0
        self.pending = None
        self.declined = set()
        os.makedirs(self.save_dir, exist_ok=True)
        self._reply_mtime = self._mtime()
        cleanup_storage(self.save_dir, self.max_storage_bytes)
    @staticmethod
    def _key(obj):
        return f"{obj.get('group')}:{obj.get('id')}"

    def send_signal(self, event_type, payload):
        self.seq += 1
        data = {"seq": self.seq, "event": event_type, "mode": self.mode,
                "timestamp": datetime.now().isoformat(), **payload}
        tmp = self.command_file + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.command_file)
        except OSError as exc:
            print(f"Could not write app command file: {exc}")
        print(f">>> [APP_SIGNAL] {json.dumps(data, ensure_ascii=False)}")

    def _save_snapshot(self, frame):
        path = os.path.join(self.save_dir, f"snap_{datetime.now():%Y%m%d_%H%M%S}_{self.seq + 1}.jpg")
        return path if cv2.imwrite(path, frame) else None

    def notify_confirmed_objects(self, confirmed, new_alerts, raw_frame, snap_frame):
        now = time.monotonic()
        self.last_confirmed_time = now
        if self.is_recording or not self.writer_ok:
            if new_alerts:
                self.send_signal("NEW_OBJECT_ALERT", {
                    "alert": True, "recording": self.is_recording, "new_objects": new_alerts,
                    **({"video_file": self.current_video_path} if self.is_recording else {})})
        elif self.mode == "auto":
            if self._start_writer((raw_frame.shape[1], raw_frame.shape[0]), now):
                self.send_signal("ALERT_AND_START_RECORDING", {
                    "alert": True, "recording": True, "objects": confirmed,
                    "video_file": self.current_video_path, "snapshot": self._save_snapshot(snap_frame)})
            else:
                self.send_signal("NEW_OBJECT_ALERT", {"alert": True, "recording": False, "new_objects": confirmed})
        else:
            self._ask_admin(confirmed, new_alerts, snap_frame, now)

    def _ask_admin(self, confirmed, new_alerts, snap_frame, now):
        fresh = [o for o in new_alerts if self._key(o) not in self.declined]
        urgent = any(o.get("group") in self.URGENT_GROUPS for o in fresh)
        if not fresh or (now < self.quiet_until and not urgent):
            return
        if self.pending is not None and not urgent:
            self.pending["objects"] = confirmed
            self.pending["trigger"] += fresh
            return
        self.alert_id += 1
        first_seen = self.pending["time"] if self.pending else now
        self.pending = {"alert_id": self.alert_id, "objects": confirmed, "trigger": list(fresh), "time": first_seen}
        self.send_signal("ALERT_ASK_RECORD", {
            "alert": True, "recording": False, "alert_id": self.alert_id, "question": "Record this event?",
            "actions": ["record", "ignore"], "urgent": urgent, "objects": confirmed,
            "snapshot": self._save_snapshot(snap_frame)})
        log_event(f"Alert #{self.alert_id}: waiting for the admin (record / ignore).")

    def handle_reply(self, action, data=None):
        action = str(action or "").strip().lower()
        now = time.monotonic()
        if action in ("record", "start", "yes"):
            self._accept_record(now)
        elif action in ("ignore", "no", "dismiss"):
            self._decline_record(now)
        elif action == "stop":
            self.stop("admin request")
        elif action == "set_mode":
            self.set_mode(str((data or {}).get("mode", "")).lower())
        else:
            print(f"Unknown app command: {action!r}")

    def _accept_record(self, now):
        if self.is_recording or not self.writer_ok:
            return
        if self.pending is None or self.last_size is None:
            log_event("Record command ignored (no alert is waiting).")
            return
        alert_id = self.pending["alert_id"]
        if self._start_writer(self.last_size, now):
            self.last_confirmed_time = now
            self.pending = None
            log_event("Admin chose: RECORD.")
            self.send_signal("RECORDING_STARTED", {
                "alert": True, "recording": True, "alert_id": alert_id, "video_file": self.current_video_path})
        else:
            self.send_signal("RECORDING_FAILED", {"alert": True, "recording": False, "alert_id": alert_id})

    def _decline_record(self, now):
        if self.pending is None:
            return
        self.declined.update(self._key(obj) for obj in self.pending["trigger"])
        self.pending = None
        self.buffer.clear()
        self.quiet_until = now + self.DISMISS_QUIET_SEC
        log_event("Admin chose: IGNORE (not recording).")

    def set_mode(self, mode):
        if mode not in self.MODES or mode == self.mode:
            return
        self.mode = mode
        if mode != "ask":
            self.pending = None
        log_event(f"Record mode: {mode.upper()}")
        self.send_signal("MODE_CHANGED", {"alert": False, "recording": self.is_recording})

    def cycle_mode(self):
        self.set_mode(self.MODES[(self.MODES.index(self.mode) + 1) % len(self.MODES)])

    def _mtime(self):
        try:
            return os.path.getmtime(self.reply_file)
        except OSError:
            return None

    def poll_reply(self):
        mtime = self._mtime()
        if mtime is None or mtime == self._reply_mtime:
            return
        try:
            with open(self.reply_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        self._reply_mtime = mtime
        if isinstance(data, dict):
            self.handle_reply(data.get("action"), data)

    def update(self, frame):
        now = time.monotonic()
        self.last_size = (frame.shape[1], frame.shape[0])
        if not self.is_recording:
            if self.writer_ok:
                self._buffer_frame(frame, now)
            return
        self._write(frame, now)
        if now - self.last_confirmed_time > self.post_roll_sec:
            self.stop("no more activity")
        elif self.max_clip_sec > 0 and now - self.started > self.max_clip_sec:
            old_path = self.current_video_path
            self._close_writer()
            if self._start_writer(self.last_size, now):
                self.send_signal("RECORDING_NEW_FILE", {
                    "alert": True, "recording": True, "saved_file": old_path, "video_file": self.current_video_path})
            else:
                self.is_recording = False
                self.send_signal("STOP_RECORDING", {"alert": False, "recording": False, "saved_file": old_path})

    def _buffer_frame(self, frame, now):
        ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        if ok:
            self.buffer.append((now, jpg))
        anchor = self.pending["time"] if self.pending else now
        cutoff = max(anchor - self.pre_roll_sec, now - self.max_buffer_sec)
        while self.buffer and self.buffer[0][0] < cutoff:
            self.buffer.popleft()

    def tick(self, now):
        idle = now - self.last_confirmed_time
        if not self.writer_ok and now - self.writer_failed_at > self.WRITER_RETRY_SEC:
            self.writer_ok = True
            log_event("Retrying video recording after an earlier failure.")
        if self.is_recording and idle > self.post_roll_sec + 2:
            self.stop("no frames")
        if self.is_recording:
            return
        if self.pending is not None and idle > self.ask_timeout_sec:
            self.send_signal("ALERT_EXPIRED", {
                "alert": False, "recording": False, "alert_id": self.pending["alert_id"]})
            log_event(f"Alert #{self.pending['alert_id']} expired without an answer.")
            self.pending = None
            self.buffer.clear()
        if idle > self.post_roll_sec + 2:
            self.declined.clear()

    def stop(self, why=""):
        if not self.is_recording:
            return
        saved = self.current_video_path
        seconds = self.frames_out / self.video_fps
        self._close_writer()
        self.is_recording = False
        log_event(f"Recording stopped ({why}): {os.path.basename(saved or '')} - {seconds:.0f}s of video")
        self.send_signal("STOP_RECORDING", {"alert": False, "recording": False, "saved_file": saved})
        cleanup_storage(self.save_dir, self.max_storage_bytes)

    def _open_writer(self, size):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for ext, codec in self.CODECS:
            path = os.path.join(self.save_dir, f"alert_{stamp}.{ext}")
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*codec), self.video_fps, size)
            if writer.isOpened():
                return writer, path
            writer.release()
            if os.path.exists(path):
                os.remove(path)
        return None, None

    def _start_writer(self, size, now):
        writer, path = self._open_writer(size)
        if writer is None:
            log_event("Recording failed: could not open a video writer (alerts only).")
            self.writer_ok, self.writer_failed_at = False, now
            self.buffer.clear()
            return False
        self.writer, self.current_video_path, self.size = writer, path, size
        self.is_recording = True
        self.started, self.t0, self.frames_out = now, None, 0
        for t, jpg in self.buffer:
            image = cv2.imdecode(jpg, cv2.IMREAD_COLOR)
            if image is not None:
                self._write(image, t)
        self.buffer.clear()
        log_event(f"Recording started: {os.path.basename(path)}")
        return True

    def _write(self, frame, t):
        if self.writer is None:
            return
        if self.t0 is None:
            self.t0 = t
        count = int((t - self.t0) * self.video_fps) + 1 - self.frames_out
        if count <= 0:
            return
        if self.size and (frame.shape[1], frame.shape[0]) != self.size:
            frame = cv2.resize(frame, self.size)
        for _ in range(count):
            self.writer.write(frame)
        self.frames_out += count

    def _close_writer(self):
        if self.writer is not None:
            self.writer.release()
            self.writer = None
