
import config  
import os
import signal
import time
import cv2
import state
from app_bridge import AppBridgeController
from cli import build_parser, load_models
from config import CAMERA_RETRY_SEC, IS_LINUX, RECORDINGS_DIR, APP_CMD_FILE, WINDOW
from controls import close_camera, open_camera, request_exit
from drawing import make_view, render_window
from pipeline import process_frame
from ui import handle_key, mouse_callback
from utils import parse_zone

def main():
    state.args = args = build_parser().parse_args()
    if IS_LINUX and not args.headless and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("No display found - switching to --headless.")
        args.headless = True
    state.mirror_on = args.mirror if args.mirror is not None else not args.headless
    if args.zone:
        state.zone_poly = parse_zone(args.zone)
    for name in ("SIGTERM", "SIGINT"):
        try:
            signal.signal(getattr(signal, name), request_exit)
        except (AttributeError, ValueError, OSError):
            pass
    load_models()
    state.app_bridge = AppBridgeController(
        RECORDINGS_DIR, APP_CMD_FILE, args.reply_file, post_roll_sec=args.post_roll, pre_roll_sec=args.pre_roll,
        max_clip_sec=args.max_clip, video_fps=args.video_fps, mode=args.record_mode,
        ask_timeout_sec=args.ask_timeout, max_buffer_sec=15.0 if IS_LINUX else 30.0,
        jpeg_quality=65 if IS_LINUX else 80, max_storage_bytes=int(args.max_storage_gb * 1024 ** 3))
    last_open_try = 0.0
    if args.headless:
        print("Smart Camera AI started in HEADLESS mode (Ctrl+C or SIGTERM to stop).")
        open_camera()
        last_open_try = time.monotonic()
    else:
        cv2.namedWindow(WINDOW)
        cv2.setMouseCallback(WINDOW, mouse_callback)
        print("Smart Camera AI started. Keys: M = mirror, R = record, N = ignore, A = record mode, Q/Esc = quit.")
    view = frame_size = None
    fps, fps_report = 0.0, time.monotonic()
    try:
        while not state.exit_program:
            state.app_bridge.poll_reply()
            state.app_bridge.tick(time.monotonic())
            if args.headless and state.cam is None:
                if time.monotonic() - last_open_try > CAMERA_RETRY_SEC:
                    last_open_try = time.monotonic()
                    open_camera()
                time.sleep(0.1)
                continue
            cam = state.cam
            result = cam.getNewFrame(state.last_frame_id, timeout=0.05 if args.headless else 0.0) if cam else None
            if result is not None:
                state.last_frame_id, frame = result
                start = time.perf_counter()
                processed = process_frame(cv2.flip(frame, 1) if state.mirror_on else frame)
                frame_size = (processed.shape[1], processed.shape[0])
                if not args.headless:
                    view = make_view(processed)
                elapsed = max(time.perf_counter() - start, 1e-6)
                fps = 0.9 * fps + 0.1 / elapsed if fps else 1 / elapsed
                if time.monotonic() - fps_report > 5:
                    fps_report = time.monotonic()
                    print(f"Processing speed: {fps:.1f} FPS")
            if args.headless:
                continue
            if state.cam is None:
                view = frame_size = None
            cv2.imshow(WINDOW, render_window(view, fps, frame_size))
            handle_key(cv2.waitKey(1) & 0xFF)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        close_camera()
        if not args.headless:
            cv2.destroyAllWindows()
        print("Smart Camera AI stopped.")

if __name__ == "__main__":
    main()
