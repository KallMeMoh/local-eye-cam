from fastapi import FastAPI

from project.core.camera import Camera

def Server(camera: Camera) -> FastAPI:
  app = FastAPI()

  app.state.camera = camera

  @app.get("/ping")
  def ping():
    return "pong"

  return app