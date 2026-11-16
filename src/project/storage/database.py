from collections.abc import Generator
from sqlite3 import Connection as SQLiteConnection
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry

from src.constants import DB_FILE_PATH

class Base(DeclarativeBase):
  pass

engine = create_engine(
  url=DB_FILE_PATH,
  pool_pre_ping=True,  
  connect_args={ "check_same_thread": False }
)
SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

@event.listens_for(engine, "connect")
def set_sqlite_pragmas(dbapi_connection: SQLiteConnection, connection_record: ConnectionPoolEntry):
  cursor = dbapi_connection.cursor()
  cursor.execute("PRAGMA journal_mode=WAL")
  cursor.execute("PRAGMA busy_timeout=5000")
  cursor.close()

def get_session() -> Generator[Session, None, None]:
  session = SessionFactory()
  try:
    yield session
  finally:
    session.close()