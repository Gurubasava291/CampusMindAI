import sqlite3
from flask import current_app, g
from pathlib import Path

def get_db():
    """Get or create database connection for the current application context."""
    if 'db' not in g:
        db_path = current_app.config['DATABASE_PATH']
        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(str(db_path))
        g.db.row_factory = sqlite3.Row
        # Enable foreign key support
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Close the database connection if open."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app=None):
    """Initialize database from schema.sql."""
    if app:
        with app.app_context():
            _execute_schema()
    else:
        _execute_schema()

def _execute_schema():
    db = get_db()
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        db.executescript(f.read())
    user_columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
    if "phone_number" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")
    if "password_changed_at" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN password_changed_at TEXT")
    db.commit()

def query_db(query, args=(), one=False):
    """Execute a read query and return list of sqlite3.Row or single Row."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=(), commit=True):
    """Execute write query (INSERT/UPDATE/DELETE) and return cursor."""
    db = get_db()
    cur = db.execute(query, args)
    if commit:
        db.commit()
    return cur

def init_app(app):
    """Register database teardown with Flask app."""
    app.teardown_appcontext(close_db)
