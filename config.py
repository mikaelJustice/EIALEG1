"""
Database module - handles SQLite connection, schema creation, and helper queries
Uses Python's built-in sqlite3 module (no external ORM needed)

NEW in v2:
  - 'league' column on teams, matches, players, news  (values: 'boys' | 'girls')
  - match_events table: tracks goal scorers and yellow cards per match
  - prize money logic lives in admin routes
  - transactions type expanded with 'match_bonus' | 'match_penalty'
"""

import sqlite3
import os
from flask import g
from werkzeug.security import generate_password_hash


def get_db(app=None):
    from flask import current_app
    if app:
        db_path = app.config['DATABASE']
    else:
        db_path = current_app.config['DATABASE']

    if 'db' not in g:
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    db_path = app.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    # USERS
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'captain')),
            team_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        )
    ''')

    # TEAMS - league column: 'boys' or 'girls'
    c.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            short_name TEXT NOT NULL,
            badge_color TEXT DEFAULT '#e74c3c',
            balance REAL DEFAULT 0.0,
            founded_year INTEGER,
            home_ground TEXT,
            league TEXT NOT NULL DEFAULT 'boys' CHECK(league IN ('boys','girls')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # PLAYERS
    c.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT NOT NULL CHECK(position IN ('GK','DEF','MID','FWD')),
            team_id INTEGER,
            price REAL DEFAULT 0.0,
            goals INTEGER DEFAULT 0,
            assists INTEGER DEFAULT 0,
            yellow_cards INTEGER DEFAULT 0,
            red_cards INTEGER DEFAULT 0,
            age INTEGER,
            shirt_number INTEGER,
            league TEXT NOT NULL DEFAULT 'boys' CHECK(league IN ('boys','girls')),
            photo_url TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        )
    ''')

    # MATCHES
    c.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            match_date TEXT NOT NULL,
            venue TEXT,
            home_goals INTEGER,
            away_goals INTEGER,
            status TEXT DEFAULT 'scheduled' CHECK(status IN ('scheduled','played','postponed')),
            matchday INTEGER DEFAULT 1,
            league TEXT NOT NULL DEFAULT 'boys' CHECK(league IN ('boys','girls')),
            prize_applied INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (home_team_id) REFERENCES teams(id),
            FOREIGN KEY (away_team_id) REFERENCES teams(id)
        )
    ''')

    # MATCH EVENTS - goal scorers, yellow cards, red cards
    c.execute('''
        CREATE TABLE IF NOT EXISTS match_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            event_type TEXT NOT NULL CHECK(event_type IN ('goal','yellow_card','red_card','assist')),
            minute INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        )
    ''')

    # LINEUPS
    c.execute('''
        CREATE TABLE IF NOT EXISTS lineups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            is_starter INTEGER DEFAULT 1,
            formation TEXT DEFAULT '4-3-3',
            pitch_row INTEGER DEFAULT 0,
            pitch_col INTEGER DEFAULT 0,
            shirt_slot INTEGER DEFAULT 0,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches(id),
            FOREIGN KEY (team_id) REFERENCES teams(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    ''')

    # TRANSFERS
    c.execute('''
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            from_team_id INTEGER,
            to_team_id INTEGER NOT NULL,
            fee REAL NOT NULL,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
            requested_by INTEGER NOT NULL,
            admin_note TEXT,
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (from_team_id) REFERENCES teams(id),
            FOREIGN KEY (to_team_id) REFERENCES teams(id),
            FOREIGN KEY (requested_by) REFERENCES users(id)
        )
    ''')

    # NEWS
    c.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general' CHECK(category IN ('general','transfer','match','announcement')),
            posted_by INTEGER NOT NULL,
            published INTEGER DEFAULT 1,
            league TEXT DEFAULT 'both' CHECK(league IN ('boys','girls','both')),
            image_url TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (posted_by) REFERENCES users(id)
        )
    ''')

    # TRANSACTIONS
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            description TEXT NOT NULL,
            transaction_type TEXT CHECK(transaction_type IN (
                'top_up','transfer_in','transfer_out','admin',
                'match_bonus','match_penalty'
            )),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        )
    ''')

    conn.commit()

    # Migrate existing DB: safely add new columns if they don't exist
    _migrate(conn)

    # Seed default admin
    existing = conn.execute("SELECT id FROM users WHERE role='admin'").fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ('admin', generate_password_hash('admin123'), 'admin')
        )
        conn.commit()
        print("Default admin created: username='admin', password='admin123'")

    conn.close()
    print("Database initialized successfully")
    app.teardown_appcontext(close_db)


def _migrate(conn):
    """Safely add new columns to existing tables without breaking data."""
    new_cols = [
        ("teams",   "league",        "TEXT NOT NULL DEFAULT 'boys'"),
        ("players", "league",        "TEXT NOT NULL DEFAULT 'boys'"),
        ("matches", "league",        "TEXT NOT NULL DEFAULT 'boys'"),
        ("matches", "prize_applied", "INTEGER DEFAULT 0"),
        ("news",    "league",        "TEXT DEFAULT 'both'"),
        ("lineups", "formation",     "TEXT DEFAULT '4-3-3'"),
        ("lineups", "pitch_row",     "INTEGER DEFAULT 0"),
        ("lineups", "pitch_col",     "INTEGER DEFAULT 0"),
        ("lineups", "shirt_slot",    "INTEGER DEFAULT 0"),
        ("news",    "image_url",     "TEXT DEFAULT NULL"),
        ("players", "photo_url",     "TEXT DEFAULT NULL"),
    ]
    for table, col, typedef in new_cols:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")
            conn.commit()
        except Exception:
            pass  # column already exists - fine
