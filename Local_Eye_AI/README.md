# Smart Camera AI

Local-compute smart surveillance camera (YOLO11 + ByteTrack) that detects people, vehicles,
animals, dangerous objects, unattended bags and fire/smoke, records clips, and talks to a mobile
app through JSON files. Runs on Windows / Linux / macOS and Raspberry Pi.

## Project structure

| File | Purpose |
|------|---------|
| `main.py` | Entry point and main loop |
| `config.py` | All constants (paths, colors, thresholds, class groups) |
| `state.py` | Shared runtime state (camera, model, tracks, ...) |
| `cli.py` | Command-line arguments + model loading |
| `camera.py` | Threaded camera reader (OpenCV / Picamera2) |
| `detection.py` | Tracking, zone confirmation, unattended bag, fire detection |
| `pipeline.py` | Per-frame processing |
| `app_bridge.py` | Alerts, recording and communication with the mobile app |
| `drawing.py` | Drawing on frames and the desktop window |
| `ui.py` | Mouse / keyboard handling |
| `controls.py` | Open/close camera, mirror, exit |
| `utils.py` | Logging, storage cleanup, zone parsing, helpers |

## Install & run

```bash
pip install -r requirements.txt
python main.py                      # desktop window
python main.py --headless           # no GUI (Raspberry Pi / server)
python main.py --record-mode ask    # admin chooses Record / Ignore
python main.py --zone "0.2,0.2,0.8,0.9"
```

Model weights (`yolo11s.pt` / `yolo11n_ncnn_model`) are downloaded/loaded by Ultralytics and are not
committed to the repo.

Keys: `M` mirror · `R` record · `N` ignore · `A` record mode · `Q`/`Esc` quit
