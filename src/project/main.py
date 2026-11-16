import logging
import uvicorn

from project.core.camera import Camera
from project.constants import API_PORT
from project.api.server import Server

def main():
  logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
  )

  camera = Camera(0)
  app = Server(camera=camera)

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

if __name__ == "__main__":
  main()
