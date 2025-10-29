from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


def init_db() -> None:
    import app.models  # noqa: F401 - ensure models are registered
    from app.models import EmojiSubmission

    SQLModel.metadata.create_all(bind=engine)

    if settings.database_url.startswith("sqlite"):
        table_name = EmojiSubmission.__table__.name
        with engine.connect() as connection:
            columns = connection.exec_driver_sql(f"PRAGMA table_info('{table_name}')").fetchall()
            if not columns:
                return
            column_names = {column[1] for column in columns}
            if "submitter_id" not in column_names:
                connection.exec_driver_sql(
                    f"ALTER TABLE {table_name} ADD COLUMN submitter_id INTEGER"
                )


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


__all__ = ["engine", "get_session", "init_db"]
