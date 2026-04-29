"""
Forge3D – Database Connection Utility
Manages a persistent PostgreSQL connection pool using psycopg2.
Reads DATABASE_URL from environment and enforces SSL.
"""

import os
import psycopg2
import psycopg2.pool
from contextlib import contextmanager

# ── Connection Pool ───────────────────────────────────────────────────────────
# Kept small for Vercel serverless (new function instance per request)
_pool: psycopg2.pool.SimpleConnectionPool | None = None


def _get_pool() -> psycopg2.pool.SimpleConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL environment variable is not set.")

        # Supabase requires sslmode=require
        if "sslmode" not in database_url:
            database_url += "?sslmode=require"

        _pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,         # low for serverless
            dsn=database_url,
        )
    return _pool


@contextmanager
def get_db():
    """
    Context manager that yields a psycopg2 connection from the pool.
    Commits on success, rolls back on exception, always returns the
    connection to the pool.

    Usage:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ...")
    """
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def close_pool():
    """Gracefully close the connection pool (call on app shutdown)."""
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
        _pool = None
