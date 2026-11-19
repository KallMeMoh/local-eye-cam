import state
from camera import Camera
from config import OPEN_ERROR_HINT
from detection import reset_tracking

def open_camera():
    if state.cam is not None:
        return
    args = state.args
    sources = [int(args.source) if args.source.isdigit() else args.source] if args.source else [0, 1, 2, 3]
    for source in sources:
        stream = Camera(source, width=args.cam_width, height=args.cam_height)
        if stream.connected:
            state.cam, state.last_frame_id = stream, 0
            reset_tracking()
            print(f"Camera source {source} opened.")
            return
        stream.release()
    print("Could not open camera. " + OPEN_ERROR_HINT)


def close_camera():
    if state.app_bridge is not None:
        state.app_bridge.stop("camera closed")
        state.app_bridge.pending = None
        state.app_bridge.buffer.clear()
    if state.cam is not None:
        state.cam.release()
        state.cam = None
    reset_tracking()
    print("Camera closed.")


def toggle_mirror():
    state.mirror_on = not state.mirror_on
    reset_tracking()
    print(f"Mirror {'ON' if state.mirror_on else 'OFF'}.")


def request_exit(signum=None, frame=None):
    state.exit_program = True
