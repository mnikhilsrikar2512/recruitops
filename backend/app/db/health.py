from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import get_engine


def get_database_health() -> str:
    try:
        engine = get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except SQLAlchemyError:
        return "error"
