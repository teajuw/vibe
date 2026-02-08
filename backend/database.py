from sqlmodel import SQLModel, create_engine, Session
from contextlib import contextmanager

from .config import settings
from .models import Song  # Import to register table

# SQLite database URL
DATABASE_URL = f"sqlite:///{settings.data_dir}/songs.db"

# Create engine
engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    """Create all tables."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    """Get a database session."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
