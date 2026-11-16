from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
import uvicorn

from .core.camera import Camera
from .constants import API_PORT
from .api.server import Server

@asynccontextmanager
async def lifespan(app: FastAPI):
  app.state.camera = Camera(0)
  transport = None
  try:
    yield
  finally:
    if transport is not None:
      transport.close()
    app.state.camera.release()

app = Server(lifespan=lifespan)

if __name__ == "__main__":
  logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
  )
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