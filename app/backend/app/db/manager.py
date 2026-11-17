"""Database connection manager with LRU cache and expiry."""

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.runtime_flags import is_safe_mode_enabled

logger = logging.getLogger(__name__)
settings = get_settings()


class ConnectionInfo:
    """Connection information with expiry."""

    def __init__(
        self,
        connection_id: str,
        engine: Engine,
        dialect: str,
        database: str,
        last_accessed: datetime,
        capabilities: dict,
    ):
        """Initialize connection info.

        Args:
            connection_id: Unique connection identifier
            engine: SQLAlchemy engine
            dialect: Database dialect (postgresql, mysql, sqlite)
            database: Database name
            last_accessed: Last access timestamp
            capabilities: Connection capabilities dict
        """
        self.connection_id = connection_id
        self.engine = engine
        self.dialect = dialect
        self.database = database
        self.last_accessed = last_accessed
        self.capabilities = capabilities

    def is_expired(self, expiry_minutes: int) -> bool:
        """Check if connection has expired.

        Args:
            expiry_minutes: Minutes until expiry

        Returns:
            True if expired, False otherwise
        """
        expiry_time = timedelta(minutes=expiry_minutes)
        return datetime.utcnow() - self.last_accessed > expiry_time

    def touch(self):
        """Update last accessed timestamp."""
        self.last_accessed = datetime.utcnow()


class ConnectionManager:
    """Manages database connections with LRU cache and expiry."""

    def __init__(self):
        """Initialize connection manager."""
        self._connections: Dict[str, ConnectionInfo] = {}
        self._expiry_minutes = settings.connection_expiry_minutes

    def build_sqlalchemy_url(
        self,
        dialect: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> str:
        """Build SQLAlchemy database URL.

        Args:
            dialect: Database dialect (postgresql, mysql, sqlite)
            username: Username (not used for SQLite)
            password: Password (not used for SQLite)
            host: Host (not used for SQLite)
            port: Port (not used for SQLite)
            database: Database name or file path for SQLite
            options: Additional connection options

        Returns:
            SQLAlchemy database URL string
        """
        options = options or {}

        if dialect == "sqlite":
            # SQLite: database is the file path or :memory:
            if not database:
                database = ":memory:"
            # Use standard sqlite driver (sync for simplicity)
            return f"sqlite:///{database}"

        elif dialect == "postgresql" or dialect == "postgres":
            # PostgreSQL: use psycopg2 driver (sync for simplicity)
            user_pass = f"{username}:{password}@" if username and password else ""
            host_port = f"{host or 'localhost'}:{port or 5432}"
            db = f"/{database}" if database else ""
            options_str = ""
            if options:
                params = "&".join(f"{k}={v}" for k, v in options.items())
                options_str = f"?{params}"
            return f"postgresql+psycopg2://{user_pass}{host_port}{db}{options_str}"

        elif dialect == "mysql" or dialect == "mariadb":
            # MySQL/MariaDB: use pymysql driver (sync for simplicity)
            user_pass = f"{username}:{password}@" if username and password else ""
            host_port = f"{host or 'localhost'}:{port or 3306}"
            db = f"/{database}" if database else ""
            options_str = ""
            if options:
                params = "&".join(f"{k}={v}" for k, v in options.items())
                options_str = f"?{params}"
            # Default charset
            if "charset" not in options:
                options_str = f"{options_str}&charset=utf8mb4" if options_str else "?charset=utf8mb4"
            return f"mysql+pymysql://{user_pass}{host_port}{db}{options_str}"

        else:
            raise ValueError(f"Unsupported dialect: {dialect}")

    def create_connection(
        self,
        dialect: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> Tuple[str, Engine, dict]:
        """Create a new database connection.

        Args:
            dialect: Database dialect
            username: Username
            password: Password
            host: Host
            port: Port
            database: Database name
            options: Additional options

        Returns:
            Tuple of (connection_id, engine, capabilities)

        Raises:
            SQLAlchemyError: If connection fails
        """
        # Build URL
        url = self.build_sqlalchemy_url(dialect, username, password, host, port, database, options)

        # Create engine
        # For async, we'll use create_async_engine but execute with sync wrappers for simplicity
        # Actually, let's use sync engines for now for simplicity, then wrap in async if needed
        if dialect == "sqlite":
            engine = create_engine(url, echo=False, pool_pre_ping=True)
        else:
            # For sync engines with async drivers, we'll use the sync API
            # Actually, let's use the standard sync drivers for now
            # We can switch to async later if performance requires it
            engine = create_engine(
                url,
                echo=False,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )

        # Test connection
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
        except SQLAlchemyError as e:
            logger.error(f"Connection test failed: {e}")
            engine.dispose()
            raise ValueError(f"Failed to connect to database: {e}") from e

        # Generate connection ID
        connection_id = str(uuid.uuid4())

        # Determine capabilities
        capabilities = {
            "readOnly": is_safe_mode_enabled(),
            "dialect": dialect,
        }

        # Store connection
        conn_info = ConnectionInfo(
            connection_id=connection_id,
            engine=engine,
            dialect=dialect,
            database=database or "default",
            last_accessed=datetime.utcnow(),
            capabilities=capabilities,
        )
        self._connections[connection_id] = conn_info

        logger.info(
            f"Created connection {connection_id} for {dialect}://{host or 'localhost'}/{database or ''}"
        )

        return connection_id, engine, capabilities

    def get_connection(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection by ID, checking expiry.

        Args:
            connection_id: Connection identifier

        Returns:
            ConnectionInfo if found and not expired, None otherwise
        """
        conn_info = self._connections.get(connection_id)
        if not conn_info:
            return None
        # Refresh read-only capability based on current safe mode toggle
        conn_info.capabilities["readOnly"] = is_safe_mode_enabled()

        if conn_info.is_expired(self._expiry_minutes):
            logger.info(f"Connection {connection_id} expired, removing")
            self.close_connection(connection_id)
            return None

        conn_info.touch()
        return conn_info

    def close_connection(self, connection_id: str) -> bool:
        """Close and remove a connection.

        Args:
            connection_id: Connection identifier

        Returns:
            True if connection was found and closed, False otherwise
        """
        conn_info = self._connections.pop(connection_id, None)
        if conn_info:
            try:
                conn_info.engine.dispose()
                logger.info(f"Closed connection {connection_id}")
            except Exception as e:
                logger.warning(f"Error closing connection {connection_id}: {e}")
            return True
        return False

    def cleanup_expired(self):
        """Remove all expired connections."""
        expired_ids = [
            conn_id
            for conn_id, conn_info in self._connections.items()
            if conn_info.is_expired(self._expiry_minutes)
        ]
        for conn_id in expired_ids:
            self.close_connection(conn_id)

    def execute_query(
        self, connection_id: str, sql: str, parameters: Optional[dict] = None
    ) -> Tuple[list, list, int]:
        """Execute a SQL query and return results.

        Args:
            connection_id: Connection identifier
            sql: SQL statement
            parameters: Query parameters (optional)

        Returns:
            Tuple of (columns, rows, row_count)

        Raises:
            ValueError: If connection not found or expired
            SQLAlchemyError: If query execution fails
        """
        conn_info = self.get_connection(connection_id)
        if not conn_info:
            raise ValueError(f"Connection {connection_id} not found or expired")

        parameters = parameters or {}

        try:
            with conn_info.engine.connect() as conn:
                # Use begin() to ensure proper transaction handling
                with conn.begin():
                    result = conn.execute(text(sql), parameters)
                    if result.returns_rows:
                        columns = list(result.keys())
                        rows = [list(row) for row in result.fetchall()]
                        row_count = len(rows)
                    else:
                        columns = []
                        rows = []
                        row_count = result.rowcount if hasattr(result, "rowcount") else 0
                    return columns, rows, row_count
        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            raise ValueError(f"Query execution failed: {e}") from e


# Global manager instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get or create global connection manager instance."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager

