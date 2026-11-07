"""Resilient database manager: PostgreSQL when DATABASE_URL answers, otherwise local SQLite.

On first use the manager probes DATABASE_URL with a short connect timeout. If the URL is unset
it uses the SQLite file quietly. If the URL is malformed, names another database, needs a
driver that is not installed, or the server does not answer, the manager fails over to SQLite
(TELEMETRY_DB_PATH, by default data/placement_nexus.db) and logs one failover event. A
PostgreSQL connection that drops out later is handled the same way: the operation that hit the
outage is retried once on SQLite, so a caller never sees the error.

There is no automatic fail-back: a restart probes PostgreSQL again. Records written to
PostgreSQL before a failover stay there, and SQLite carries on from whatever it already holds.
Log lines and events show the URL with its password hidden.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from threading import RLock

from sqlalchemy import URL, Engine, create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from database.models import Base, utc_now
from piq.config import DB_CONNECT_TIMEOUT, settings

log = logging.getLogger("database")

POSTGRES, SQLITE = "postgresql", "sqlite"
# Errors that mean "the server is gone", as opposed to a bad query or a broken constraint.
_OUTAGES = (OperationalError, InterfaceError)


@dataclass(frozen=True)
class FailoverEvent:
    at: datetime
    reason: str  # why PostgreSQL was given up, password removed
    fallback: Path  # the SQLite file now in use


def safe_url(url: str) -> str:
    """The URL as it may be logged: password hidden, or a placeholder if it does not parse."""
    try:
        return make_url(url).render_as_string(hide_password=True)
    except SQLAlchemyError:
        return "<unparseable DATABASE_URL>"


class DatabaseManager:
    """One backend at a time, chosen lazily on first use; see the module docstring."""

    def __init__(
        self,
        database_url: str = "",
        sqlite_path: Path | str = Path("data") / "placement_nexus.db",
        connect_timeout: int = DB_CONNECT_TIMEOUT,
    ) -> None:
        self.database_url = database_url.strip()
        self.sqlite_path = Path(sqlite_path)
        self.connect_timeout = max(1, int(connect_timeout))
        self.events: list[FailoverEvent] = []
        self.backend: str | None = None  # POSTGRES or SQLITE once connected
        self._engine: Engine | None = None
        self._lock = RLock()

    # --- choosing a backend -------------------------------------------------------------
    @property
    def engine(self) -> Engine:
        with self._lock:
            if self._engine is None:
                self._connect()
            assert self._engine is not None
            return self._engine

    @property
    def failed_over(self) -> bool:
        return bool(self.events)

    def _connect(self) -> None:
        if not self.database_url:
            log.info("DATABASE_URL is not set; telemetry uses SQLite at %s", self.sqlite_path)
            self._use_sqlite()
            return
        try:
            engine = self._postgres_engine()
            self._probe(engine)
        except (SQLAlchemyError, ImportError, ValueError) as e:
            self._fail_over(e)
            return
        self._engine, self.backend = engine, POSTGRES
        log.info("Telemetry connected to PostgreSQL at %s", safe_url(self.database_url))

    def _postgres_engine(self) -> Engine:
        url = make_url(self.database_url)
        if url.drivername in ("postgres", "postgresql"):  # the bare scheme means psycopg 3 here
            url = url.set(drivername="postgresql+psycopg")
        if url.get_backend_name() != POSTGRES:
            raise ValueError(f"DATABASE_URL names {url.get_backend_name()!r}, not PostgreSQL")
        return create_engine(
            url, pool_pre_ping=True, connect_args={"connect_timeout": self.connect_timeout}
        )

    def _probe(self, engine: Engine) -> None:
        """Connect, run a trivial query and create the tables; raises if the server is not
        usable."""
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        Base.metadata.create_all(engine)

    def _use_sqlite(self) -> None:
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(URL.create("sqlite", database=str(self.sqlite_path)))

        @event.listens_for(engine, "connect")
        def _foreign_keys(dbapi_conn, _record) -> None:  # SQLite leaves them off by default
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        Base.metadata.create_all(engine)
        self._engine, self.backend = engine, SQLITE

    def _reason(self, error: BaseException) -> str:
        cause = error.orig if isinstance(error, DBAPIError) and error.orig else error
        lines = str(cause).strip().splitlines()
        message = lines[0] if lines else type(cause).__name__
        try:
            password = make_url(self.database_url).password
        except SQLAlchemyError:
            password = None
        if password:
            message = message.replace(str(password), "***")
        return f"{type(error).__name__}: {message}"

    def _fail_over(self, error: BaseException) -> None:
        with self._lock:
            reason = self._reason(error)
            if self._engine is not None and self.backend == POSTGRES:
                self._engine.dispose()
            self._use_sqlite()
            self.events.append(FailoverEvent(utc_now(), reason, self.sqlite_path))
            log.warning(
                "Telemetry failover: PostgreSQL at %s unavailable (%s); using SQLite at %s",
                safe_url(self.database_url),
                reason,
                self.sqlite_path,
            )

    # --- running work ---------------------------------------------------------------------
    def run[T](self, work: Callable[[Session], T]) -> T:
        """Run `work(session)` in one transaction: committed if it returns, rolled back if it
        raises. If PostgreSQL drops out (and a fresh probe confirms it), fail over and run
        `work` once more on SQLite. Any other error reaches the caller."""
        try:
            return self._run(work)
        except _OUTAGES as e:
            if self.backend != POSTGRES or self._still_alive():
                raise
            self._fail_over(e)
            return self._run(work)

    def _run[T](self, work: Callable[[Session], T]) -> T:
        with Session(self.engine, expire_on_commit=False) as session, session.begin():
            return work(session)

    def _still_alive(self) -> bool:
        try:
            self._probe(self.engine)
        except (SQLAlchemyError, OSError):
            return False
        return True

    def dispose(self) -> None:
        with self._lock:
            if self._engine is not None:
                self._engine.dispose()
            self._engine, self.backend = None, None


@lru_cache(maxsize=1)
def get_manager() -> DatabaseManager:
    """The process-wide manager, configured from settings (DATABASE_URL, TELEMETRY_DB_PATH)."""
    s = settings()
    return DatabaseManager(s.database_url, s.telemetry_db_path)


def reset_manager() -> None:
    """Drop the process-wide manager (tests; or to probe PostgreSQL again after an outage)."""
    if get_manager.cache_info().currsize:
        get_manager().dispose()
    get_manager.cache_clear()
