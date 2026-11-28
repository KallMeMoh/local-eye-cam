from firebase_admin import get_app, initialize_app, credentials, messaging

class PushNotifier:
  def __init__(self, key_path: str) -> None:
    try:
      _ = get_app()
    except ValueError:
      _ = initialize_app(credentials.Certificate(key_path))

  def broadcast(
    self,
    title: str,
    body: str,
    topic: str = "all",
    data: dict[str, str] | None = None,
  ) -> str:
    msg = messaging.Message(
      notification=messaging.Notification(title=title, body=body),
      data=data or {},
      topic=topic,
    )
    return messaging.send(msg)