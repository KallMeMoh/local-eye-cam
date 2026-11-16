from fastapi import FastAPI
from starlette.types import Lifespan

def Server(lifespan: Lifespan[FastAPI] | None) -> FastAPI:
  app = FastAPI(lifespan=lifespan)

  @app.get("/ping")
  def ping():
    return "pong"

  return app