"""Database layer: SQLite by default, with optional MySQL via DATABASE_URL."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
DB_PATH = INSTANCE_DIR / "crop_history.db"


def _make_engine() -> Engine:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    default_url = f"sqlite:///{DB_PATH.as_posix()}"
    url = os.environ.get("DATABASE_URL", default_url)
    if url.startswith("sqlite:"):
        return create_engine(url, connect_args={"check_same_thread": False}, future=True)
    # Supports MySQL URLs such as mysql+pymysql://user:password@localhost:3306/crop_disease_db
    return create_engine(url, pool_pre_ping=True, future=True)


engine = _make_engine()


def init_db() -> None:
    """Create the prediction table if it does not exist."""
    if engine.dialect.name == "mysql":
        ddl = """CREATE TABLE IF NOT EXISTS predictions (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            created_at VARCHAR(40) NOT NULL,
            crop VARCHAR(100) NOT NULL,
            disease VARCHAR(200) NOT NULL,
            confidence DOUBLE NOT NULL
        )"""
    else:
        ddl = """CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            crop TEXT NOT NULL,
            disease TEXT NOT NULL,
            confidence REAL NOT NULL
        )"""
    with engine.begin() as conn:
        conn.execute(text(ddl))


def get_recent_predictions(limit: int = 6) -> list[dict[str, Any]]:
    statement = text(
        "SELECT id, created_at, crop, disease, confidence "
        "FROM predictions ORDER BY id DESC LIMIT :limit"
    )
    with engine.connect() as conn:
        rows = conn.execute(statement, {"limit": int(limit)}).mappings().all()
    return [dict(row) for row in rows]


def save_prediction(crop: str, disease: str, confidence: float) -> None:
    statement = text(
        "INSERT INTO predictions (created_at, crop, disease, confidence) "
        "VALUES (:created_at, :crop, :disease, :confidence)"
    )
    from datetime import datetime
    with engine.begin() as conn:
        conn.execute(statement, {
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "crop": crop,
            "disease": disease,
            "confidence": float(confidence),
        })
