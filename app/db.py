from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={'check_same_thread': False, 'timeout': 30} if settings.database_url.startswith('sqlite') else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


if settings.database_url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def _sqlite_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA busy_timeout=30000')
        cursor.close()


def init_db() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    from app.models import Job  # noqa: F401

    Base.metadata.create_all(bind=engine)
