"""Private SQLite operations. Backups include document text and identity digests."""

from contextlib import closing
import hashlib
import os
from pathlib import Path
import sqlite3


def inspect_database(database):
    path = Path(database)
    if path.is_symlink() or not path.is_file():
        raise ValueError("EXISTING_DATABASE_REQUIRED")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise ValueError("DATABASE_INTEGRITY_FAILED")
        required = {"identities", "documents", "chunks"}
        tables = {
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if not required <= tables:
            raise ValueError("DATABASE_SCHEMA_MISMATCH")
        columns = {
            "identities": {"subject", "digest", "tenant", "role", "revoked"},
            "documents": {
                "id",
                "tenant",
                "doc_id",
                "version",
                "title",
                "topic",
                "effective_on",
                "expires_on",
                "min_role",
                "sha256",
                "fingerprint",
                "filename",
                "current",
                "deleted",
            },
            "chunks": {"id", "document", "text", "page", "locator"},
        }
        for table, required_columns in columns.items():
            if not required_columns <= {
                row[1] for row in db.execute("PRAGMA table_info(" + table + ")")
            }:
                raise ValueError("DATABASE_SCHEMA_MISMATCH")
        # Exercise required columns, not just matching table names.
        db.execute("SELECT subject,digest,tenant,role,revoked FROM identities LIMIT 0")
        db.execute(
            "SELECT tenant,doc_id,version,current,deleted FROM documents LIMIT 0"
        )
        db.execute("SELECT document,text,page,locator FROM chunks LIMIT 0")
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("DATABASE_REFERENTIAL_INTEGRITY_FAILED")
        counts = {
            name: db.execute("SELECT COUNT(*) FROM " + name).fetchone()[0]
            for name in sorted(required)
        }
    return {
        "status": "HEALTHY",
        "schema": "localrag-v1",
        "counts": counts,
        "private_permissions": not bool(path.stat().st_mode & 0o077),
    }


def copy_database(source, destination):
    """SQLite online backup API captures committed WAL data; never overwrite."""
    source, destination = Path(source), Path(destination)
    inspect_database(source)
    if not destination.parent.is_dir():
        raise ValueError("EXISTING_DESTINATION_DIRECTORY_REQUIRED")
    descriptor = os.open(
        destination,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    os.close(descriptor)
    try:
        with closing(
            sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
        ) as src:
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
        health = inspect_database(destination)
        with destination.open("rb") as handle:
            os.fsync(handle.fileno())
        return {
            "status": "COPIED",
            "schema": health["schema"],
            "counts": health["counts"],
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "contains_private_data": True,
        }
    except Exception:
        destination.unlink(missing_ok=True)
        raise
