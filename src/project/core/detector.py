import time
import cv2
from ultralytics import YOLO

class AIDetector:
    def __init__(self, model_path="yolo11n.pt", alert_duration=1.0, conf=0.4):
        self.model = YOLO(model_path)
        self.alert_duration = alert_duration
        self.conf = conf
        self.zone_enter_time = None
        self.alert_sent = False

    def process_frame(self, frame):
        h, w = frame.shape[:2]
        zone = (5, 5, w - 5, h - 5)

        results = self.model(frame, imgsz=640, conf=self.conf, verbose=False)
        in_zone = False
        detected_labels = []

        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            detected_labels.append(self.model.names[cls_id])

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            if zone[0] < cx < zone[2] and zone[1] < cy < zone[3]:
                in_zone = True

        alert_triggered = False
        if in_zone:
            if self.zone_enter_time is None:
                self.zone_enter_time = time.time()
            elif time.time() - self.zone_enter_time >= self.alert_duration and not self.alert_sent:
                alert_triggered = True
                self.alert_sent = True
        else:
            self.zone_enter_time = None
            self.alert_sent = False

        annotated_frame = results[0].plot()
        color = (0, 0, 255) if self.alert_sent else (0, 255, 0)
        cv2.rectangle(annotated_frame, (zone[0], zone[1]), (zone[2], zone[3]), color, 2)

        inference_ms = results[0].speed["inference"]
        fps = 1000 / inference_ms if inference_ms > 0 else 0
        cv2.putText(annotated_frame, f"FPS: {fps:.1f}", (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        return annotated_frame, alert_triggered, detected_labels