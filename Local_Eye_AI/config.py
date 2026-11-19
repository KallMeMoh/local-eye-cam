import os
import platform
SYSTEM = platform.system()
IS_LINUX = SYSTEM == "Linux"
if IS_LINUX:
    os.environ.setdefault("OMP_NUM_THREADS", "3")
    os.environ.setdefault("MKL_NUM_THREADS", "3")
import cv2  

BACKENDS = {"Windows": [cv2.CAP_DSHOW, cv2.CAP_MSMF], "Linux": [cv2.CAP_V4L2],
            "Darwin": [cv2.CAP_AVFOUNDATION]}.get(SYSTEM, [cv2.CAP_ANY])
OPEN_ERROR_HINT = {
    "Linux": "Check camera cable, libcamera/picamera2, or 'video' group.",
    "Windows": "Check camera privacy settings and that no other app uses it.",
    "Darwin": "Allow camera access for Terminal/IDE in System Settings.",
}.get(SYSTEM, "")
RECONNECT_DELAY, CAMERA_RETRY_SEC = 2.0, 5.0
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "security_events.txt")
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
APP_CMD_FILE = os.path.join(BASE_DIR, "app_command.json")
APP_REPLY_FILE = os.path.join(BASE_DIR, "app_reply.json")
LOG_MAX_BYTES = 1_000_000

WINDOW = "Smart Camera AI"
WIDTH, HEIGHT, VIEW_TOP, PREVIEW_HEIGHT = 900, 600, 4, 495
FONT = cv2.FONT_HERSHEY_SIMPLEX
RED, ORANGE, WHITE = (0, 0, 255), (0, 200, 255), (255, 255, 255)
OPEN_BTN, CLOSE_BTN = (40, 520, 240, 575), (260, 520, 460, 575)
MIRROR_BTN, EXIT_BTN = (480, 520, 660, 575), (680, 520, 860, 575)
REC_YES_BTN, REC_NO_BTN = (200, 455, 430, 495), (450, 455, 700, 495)
CONFIRM_SECONDS, ZONE_GRACE, UNATTENDED_AFTER = 1.0, 0.8, 30.0
MOVE_TOLERANCE, MIN_FRAMES, MIN_BOX_RATIO, STALE_AFTER = 0.05, 2, 0.002, 10.0
FIRE_CONFIRM, FIRE_COOLDOWN = 2, 30.0
TRACK_CONF, NMS_IOU = 0.25, 0.5
CLASS_GROUPS = {
    "person": ["person"],
    "vehicle": ["bicycle", "car", "motorcycle", "bus", "truck"],
    "animal": ["bird", "cat", "dog", "horse", "sheep", "cow"],
    "bag": ["backpack", "handbag", "suitcase"],
    "danger": ["knife", "scissors", "baseball bat"],}
GROUP_CONF = {"person": 0.45, "vehicle": 0.45, "animal": 0.45, "bag": 0.50, "danger": 0.45}
GROUP_COLOR = {"person": (0, 255, 0), "vehicle": (255, 160, 0), "animal": (0, 200, 255),"bag": (255, 0, 200), "danger": RED}
ALERT_GROUPS = {"person", "vehicle", "animal", "danger"}
UNATTENDED_GROUPS = {"bag"}
NAME_TO_GROUP = {name: group for group, names in CLASS_GROUPS.items() for name in names}
