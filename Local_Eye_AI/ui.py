import cv2
import state
from config import CLOSE_BTN, EXIT_BTN, MIRROR_BTN, OPEN_BTN, REC_NO_BTN, REC_YES_BTN
from controls import close_camera, open_camera, toggle_mirror

def inside(button, x, y):
    return button[0] <= x <= button[2] and button[1] <= y <= button[3]

def mouse_callback(event, x, y, flags, param):
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    bridge = state.app_bridge
    waiting = bridge is not None and bridge.pending is not None
    if waiting and inside(REC_YES_BTN, x, y):
        bridge.handle_reply("record")
    elif waiting and inside(REC_NO_BTN, x, y):
        bridge.handle_reply("ignore")
    elif inside(OPEN_BTN, x, y):
        open_camera()
    elif inside(CLOSE_BTN, x, y):
        close_camera()
    elif inside(MIRROR_BTN, x, y):
        toggle_mirror()
    elif inside(EXIT_BTN, x, y):
        state.exit_program = True

def handle_key(key):
    if key in (27, ord("q")):
        state.exit_program = True
    elif key == ord("m"):
        toggle_mirror()
    elif key == ord("r"):
        state.app_bridge.handle_reply("record")
    elif key == ord("n"):
        state.app_bridge.handle_reply("ignore")
    elif key == ord("a"):
        state.app_bridge.cycle_mode()
