import logging
import uvicorn

from project.core.camera import Camera
from project.constants import API_PORT, FCM_KEY_PATH
from project.api.server import Server
from project.core.notifier import PushNotifier
from project.storage.database import engine, init_db 

def main():
  logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
  )

  init_db()

  push_notifier = PushNotifier(key_path=FCM_KEY_PATH)  # pyright: ignore[reportUnusedVariable] temporarily
  # Camera depends on it but I think I will pass it the push 
  # notifier after it's migrated from opencv to picamera2
  camera = Camera(0) 
  app = Server(camera=camera) 
  # If the backend ever needs it we'll pass it just like 
  # camera and attach it on app.state

  try:
    uvicorn.run(
      app=app,
      host="0.0.0.0",
      port=API_PORT,
      limit_concurrency=30,
      backlog=16,
      timeout_keep_alive=5,
      timeout_graceful_shutdown=3,
      log_config=None
    )
  finally:
    camera.release()
    engine.dispose()

if __name__ == "__main__":
  main()
