"""Threaded camera reader (OpenCV + optional Picamera2 on Raspberry Pi)."""
from threading import Condition, Event, Thread

import cv2

from config import BACKENDS, IS_LINUX, RECONNECT_DELAY, SYSTEM

try:
    from picamera2 import Picamera2
    HAS_PICAMERA2 = True
except ImportError:
    HAS_PICAMERA2 = False


def open_capture(source, width, height):
    local = isinstance(source, int) or str(source).startswith("/dev/video")
    cap = None
    for backend in (BACKENDS if local else [None]):
        cap = cv2.VideoCapture(source) if backend is None else cv2.VideoCapture(source, backend)
        if not local or cap.isOpened():
            break
        cap.release()
    if local and cap.isOpened():
        if SYSTEM != "Darwin":
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


class Camera:
    def __init__(self, source=0, width=1280, height=720, auto_reconnect=True):
        self._source, self._width, self._height = source, width, height
        self._auto_reconnect = auto_reconnect
        self._halt = Event()
        self._frame, self._frame_id = None, 0
        self._frame_condition = Condition()
        self._picam = self._cap = None
        self._connected = False
        if IS_LINUX and HAS_PICAMERA2 and isinstance(source, int):
            self._start_picamera()
        if self._picam is None:
            self._cap = self._open()
            self._connected = self._cap is not None
        self._thread = Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    @property
    def connected(self):
        return self._connected

    def _start_picamera(self):
        try:
            self._picam = Picamera2(self._source)
            self._picam.configure(self._picam.create_preview_configuration(
                main={"size": (self._width, self._height), "format": "RGB888"}))
            self._picam.start()
            self._connected = True
            print(f"Picamera2 started on camera {self._source} ({self._width}x{self._height}).")
        except Exception as exc:
            print(f"Picamera2 unavailable ({exc}), falling back to OpenCV...")
            self._close_picamera()

    def _close_picamera(self):
        if self._picam is None:
            return
        for action in (self._picam.stop, self._picam.close):
            try:
                action()
            except Exception:
                pass
        self._picam = None

    def _open(self):
        cap = open_capture(self._source, self._width, self._height)
        if cap.isOpened() and cap.read()[0]:
            return cap
        cap.release()
        return None

    def _publish(self, frame):
        with self._frame_condition:
            self._frame = frame
            self._frame_id += 1
            self._frame_condition.notify_all()
        self._connected = True

    def _capture_loop(self):
        cap = self._cap
        try:
            while not self._halt.is_set():
                if self._picam is not None:
                    try:
                        self._publish(self._picam.capture_array())
                    except Exception:
                        self._connected = False
                        self._halt.wait(RECONNECT_DELAY)
                elif cap is None:
                    if not self._auto_reconnect or self._halt.wait(RECONNECT_DELAY):
                        break
                    cap = self._open()
                    self._connected = cap is not None
                else:
                    ok, frame = cap.read()
                    if ok:
                        self._publish(frame)
                    else:
                        self._connected = False
                        cap.release()
                        cap = None
        finally:
            self._close_picamera()
            if cap is not None:
                cap.release()
            self._connected = False

    def getNewFrame(self, last_id=0, timeout=0.0):
        with self._frame_condition:
            if timeout > 0:
                self._frame_condition.wait_for(
                    lambda: self._frame_id != last_id or self._halt.is_set(), timeout)
            if self._frame is None or self._frame_id == last_id:
                return None
            return self._frame_id, self._frame.copy()

    def release(self):
        self._halt.set()
        with self._frame_condition:
            self._frame_condition.notify_all()
        self._thread.join(timeout=3)
