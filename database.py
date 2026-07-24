import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "board.db")

DEFAULT_CATEGORIES = [
    {"id": "cat_1", "label": "Standard", "color": "#2980b9"},
    {"id": "cat_2", "label": "Urgent", "color": "#c0392b"},
    {"id": "cat_3", "label": "Pending Docs", "color": "#f39c12"}
]

DEFAULT_COLUMNS = [
    {"id": "col_intake", "label": "Intake", "color": "#2b3647", "is_intake": 1, "position": 0},
    {"id": "col_file", "label": "File", "color": "#27ae60", "is_intake": 0, "position": 1},
    {"id": "col_handoff", "label": "Handoff", "color": "#8e44ad", "is_intake": 0, "position": 2},
    {"id": "col_doing", "label": "Doing", "color": "#f39c12", "is_intake": 0, "position": 3},
    {"id": "col_done", "label": "Done", "color": "#7f8c8d", "is_intake": 0, "position": 4},
]

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id TEXT PRIMARY KEY,
        label TEXT,
        color TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS columns (
        id TEXT PRIMARY KEY,
        label TEXT,
        color TEXT,
        is_intake INTEGER,
        position INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cards (
        id TEXT PRIMARY KEY,
        text TEXT,
        column_id TEXT,
        category_id TEXT,
        created_at TEXT,
        position INTEGER,
        alarm_time TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id TEXT PRIMARY KEY,
        text TEXT,
        position INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT,
        action TEXT,
        card TEXT,
        detail TEXT
    )
    """)

    # Run DB migration for existing databases to add `alarm_time` column safely
    try:
        cursor.execute("ALTER TABLE cards ADD COLUMN alarm_time TEXT")
    except sqlite3.OperationalError:
        pass

    # Seed Default Data if empty
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO settings (key, value) VALUES ('board_title', 'Document board')")
        cursor.execute("INSERT INTO settings (key, value) VALUES ('version', '1')")

    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        for cat in DEFAULT_CATEGORIES:
            cursor.execute("INSERT INTO categories (id, label, color) VALUES (?, ?, ?)", (cat["id"], cat["label"], cat["color"]))

    cursor.execute("SELECT COUNT(*) FROM columns")
    if cursor.fetchone()[0] == 0:
        for col in DEFAULT_COLUMNS:
            cursor.execute("INSERT INTO columns (id, label, color, is_intake, position) VALUES (?, ?, ?, ?, ?)",
                           (col["id"], col["label"], col["color"], col["is_intake"], col["position"]))

    conn.commit()
    conn.close()

def get_board_data():
    conn = get_connection()
    cursor = conn.cursor()

    # Board Title
    cursor.execute("SELECT value FROM settings WHERE key = 'board_title'")
    row = cursor.fetchone()
    board_title = row["value"] if row else "Document board"

    # Version
    cursor.execute("SELECT value FROM settings WHERE key = 'version'")
    row = cursor.fetchone()
    version = int(row["value"]) if row else 1

    # Categories
    cursor.execute("SELECT id, label, color FROM categories")
    categories_list = [dict(r) for r in cursor.fetchall()]

    # Columns
    cursor.execute("SELECT id, label, color, is_intake FROM columns ORDER BY position ASC")
    columns_list = []
    for r in cursor.fetchall():
        columns_list.append({
            "id": r["id"],
            "label": r["label"],
            "color": r["color"],
            "is_intake": bool(r["is_intake"])
        })

    # Cards
    cursor.execute("SELECT id, text, column_id, category_id, created_at, alarm_time FROM cards ORDER BY position ASC")
    cards_list = [dict(r) for r in cursor.fetchall()]

    # Notes
    cursor.execute("SELECT id, text FROM notes ORDER BY position ASC")
    notes_list = [dict(r) for r in cursor.fetchall()]

    # History
    cursor.execute("SELECT time, action, card, detail FROM history ORDER BY id ASC")
    history_list = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "version": version,
        "board_title": board_title,
        "categories": categories_list,
        "columns": columns_list,
        "cards": cards_list,
        "notes": notes_list,
        "history": history_list
    }

def increment_version(cursor):
    cursor.execute("SELECT value FROM settings WHERE key = 'version'")
    row = cursor.fetchone()
    current_version = int(row["value"]) if row else 1
    new_version = current_version + 1
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('version', ?)", (str(new_version),))
    return new_version

def get_version():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'version'")
    row = cursor.fetchone()
    version = int(row["value"]) if row else 1
    conn.close()
    return version

def add_card(card_id, text, column_id, category_id, created_at, alarm_time=None):
    conn = get_connection()
    cursor = conn.cursor()

    # Get current max position to append
    cursor.execute("SELECT COALESCE(MAX(position), 0) FROM cards WHERE column_id = ?", (column_id,))
    max_pos = cursor.fetchone()[0]

    cursor.execute("""
    INSERT INTO cards (id, text, column_id, category_id, created_at, position, alarm_time)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (card_id, text, column_id, category_id, created_at, max_pos + 1, alarm_time))

    # Log event
    cursor.execute("""
    INSERT INTO history (time, action, card, detail)
    VALUES (?, 'created', ?, ?)
    """, (created_at, text, f"Assigned to {column_id}"))

    new_ver = increment_version(cursor)
    conn.commit()
    conn.close()
    return new_ver

def delete_card(card_id, text, column_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))

    # Log event
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO history (time, action, card, detail)
    VALUES (?, 'deleted', ?, ?)
    """, (now_str, text, f"Removed from {column_id}"))

    new_ver = increment_version(cursor)
    conn.commit()
    conn.close()
    return new_ver

def update_cards_batch(cards):
    conn = get_connection()
    cursor = conn.cursor()

    # Clear existing cards and bulk insert with correct positions
    cursor.execute("DELETE FROM cards")
    for idx, card in enumerate(cards):
        cursor.execute("""
        INSERT INTO cards (id, text, column_id, category_id, created_at, position, alarm_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (card["id"], card["text"], card["column_id"], card["category_id"], card["created_at"], idx, card.get("alarm_time")))

    # Log event
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO history (time, action, card, detail)
    VALUES (?, 'updated', 'Cards batch processed', '')
    """, (now_str,))

    new_ver = increment_version(cursor)
    conn.commit()
    conn.close()
    return new_ver

def update_notes(notes):
    conn = get_connection()
    cursor = conn.cursor()

    # Clear existing notes and bulk insert with correct positions
    cursor.execute("DELETE FROM notes")
    for idx, note in enumerate(notes):
        cursor.execute("""
        INSERT INTO notes (id, text, position)
        VALUES (?, ?, ?)
        """, (note["id"], note["text"], idx))

    new_ver = increment_version(cursor)
    conn.commit()
    conn.close()
    return new_ver

def configure_board(board_title, columns, categories):
    conn = get_connection()
    cursor = conn.cursor()

    # Save board title
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('board_title', ?)", (board_title,))

    # Sync Categories
    cursor.execute("DELETE FROM categories")
    for cat in categories:
        cursor.execute("INSERT INTO categories (id, label, color) VALUES (?, ?, ?)", (cat["id"], cat["label"], cat["color"]))

    # Sync Columns
    cursor.execute("DELETE FROM columns")
    for idx, col in enumerate(columns):
        cursor.execute("INSERT INTO columns (id, label, color, is_intake, position) VALUES (?, ?, ?, ?, ?)",
                       (col["id"], col["label"], col["color"], 1 if col.get("is_intake") else 0, idx))

    # Log event
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO history (time, action, card, detail)
    VALUES (?, 'configured', 'Layout and categories updated', '')
    """, (now_str,))

    new_ver = increment_version(cursor)
    conn.commit()
    conn.close()
    return new_ver

def restore_backup(data):
    conn = get_connection()
    cursor = conn.cursor()

    # Clear all existing data
    cursor.execute("DELETE FROM settings")
    cursor.execute("DELETE FROM categories")
    cursor.execute("DELETE FROM columns")
    cursor.execute("DELETE FROM cards")
    cursor.execute("DELETE FROM notes")
    cursor.execute("DELETE FROM history")

    # Restore Board Title and Version
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('board_title', ?)", (data.get("board_title", "Document board"),))

    # We always bump layout/version on restore to notify active clients
    cursor.execute("SELECT value FROM settings WHERE key = 'version'")
    v = data.get("version", 1) + 1
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('version', ?)", (str(v),))

    # Restore Categories
    for cat in data.get("categories", []):
        cursor.execute("INSERT INTO categories (id, label, color) VALUES (?, ?, ?)", (cat["id"], cat["label"], cat["color"]))

    # Restore Columns
    for idx, col in enumerate(data.get("columns", [])):
        cursor.execute("INSERT INTO columns (id, label, color, is_intake, position) VALUES (?, ?, ?, ?, ?)",
                       (col["id"], col["label"], col["color"], 1 if col.get("is_intake") else 0, idx))

    # Restore Cards
    for idx, card in enumerate(data.get("cards", [])):
        cursor.execute("INSERT INTO cards (id, text, column_id, category_id, created_at, position, alarm_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (card["id"], card["text"], card["column_id"], card["category_id"], card["created_at"], idx, card.get("alarm_time")))

    # Restore Notes
    for idx, note in enumerate(data.get("notes", [])):
        cursor.execute("INSERT INTO notes (id, text, position) VALUES (?, ?, ?)", (note["id"], note["text"], idx))

    # Restore History
    for r in data.get("history", []):
        cursor.execute("INSERT INTO history (time, action, card, detail) VALUES (?, ?, ?, ?)",
                       (r.get("time", ""), r.get("action", ""), r.get("card", ""), r.get("detail", "")))

    conn.commit()
    conn.close()
