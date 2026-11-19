import argparse
import os
from ultralytics import YOLO
import state
from app_bridge import AppBridgeController
from config import APP_REPLY_FILE, IS_LINUX, NAME_TO_GROUP

def build_parser():
    p = argparse.ArgumentParser(description="Smart Camera AI (Desktop + Raspberry Pi)")
    p.add_argument("--source", default=None)
    p.add_argument("--model", default="yolo11n_ncnn_model" if IS_LINUX else "yolo11s.pt")
    p.add_argument("--imgsz", type=int, default=416 if IS_LINUX else 640)
    p.add_argument("--cam-width", type=int, default=800 if IS_LINUX else 1280)
    p.add_argument("--cam-height", type=int, default=600 if IS_LINUX else 720)
    p.add_argument("--device", default="cpu")
    p.add_argument("--mirror", action=argparse.BooleanOptionalAction, default=None,
    help="flip the image horizontally (default: ON with a window, OFF in --headless)")
    p.add_argument("--headless", action="store_true", help="no GUI window; auto-opens the camera")
    p.add_argument("--zone", default=None, help="'l,t,r,b' or 'x1,y1;x2,y2;x3,y3;...' (fractions 0..1)")
    p.add_argument("--record-mode", choices=AppBridgeController.MODES, default="auto",
    help="auto = record on detection; ask = the admin chooses Record / Ignore")
    p.add_argument("--reply-file", default=APP_REPLY_FILE)
    p.add_argument("--pre-roll", type=float, default=2.0)
    p.add_argument("--post-roll", type=float, default=10.0)
    p.add_argument("--max-clip", type=float, default=120.0, help="max seconds per video file (0 = no limit)")
    p.add_argument("--video-fps", type=float, default=20.0)
    p.add_argument("--ask-timeout", type=float, default=45.0)
    p.add_argument("--max-storage-gb", type=float, default=5.0, help="max recordings size (0 = unlimited)")
    p.add_argument("--record-overlay", action="store_true", help="record the annotated frame")
    p.add_argument("--fire-model", default=None)
    p.add_argument("--fire-every", type=int, default=5)
    p.add_argument("--fire-conf", type=float, default=0.5)
    return p

def load_models():
    args = state.args
    model_path = args.model
    if not os.path.exists(model_path) and model_path.endswith("_ncnn_model"):
        print(f"NCNN model '{model_path}' not found, falling back to 'yolo11n.pt' (slower)...")
        model_path = "yolo11n.pt"
    state.model = YOLO(model_path, task="detect")
    state.target_class_ids = [i for i, name in state.model.names.items() if name in NAME_TO_GROUP] or None
    if args.fire_model and os.path.exists(args.fire_model):
        state.fire_model = YOLO(args.fire_model, task="detect")
    elif args.fire_model:
        print(f"Fire model not found: {args.fire_model} (fire detection off)")
