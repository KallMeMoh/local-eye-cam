from config import CLASS_GROUPS

args = model = fire_model = target_class_ids = cam = app_bridge = zone_poly = None
last_frame_id = 0
mirror_on, exit_program = True, False
tracks = {}
seen_ids = {group: set() for group in CLASS_GROUPS}
fire_state = {"boxes": [], "hits": 0, "last_alert": 0.0, "frame_no": 0}
