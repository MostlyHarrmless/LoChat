import sqlite3
import hashlib
import uuid
import os
from datetime import datetime

# Absolute path enforcement
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "chat.db")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            bio TEXT DEFAULT 'Available',
            avatar_base64 TEXT DEFAULT '',
            is_banned INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            creator_id INTEGER NOT NULL,
            password TEXT DEFAULT '',
            avatar_base64 TEXT DEFAULT '',
            FOREIGN KEY(creator_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS room_members (
            room_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (room_id, user_id),
            FOREIGN KEY(room_id) REFERENCES rooms(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER,
            sender_id INTEGER,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            status TEXT DEFAULT 'sent',
            FOREIGN KEY(room_id) REFERENCES rooms(id),
            FOREIGN KEY(sender_id) REFERENCES users(id)
        )
    ''')

    # Graceful migrations for existing databases
    try: cursor.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE messages ADD COLUMN status TEXT DEFAULT 'sent'")
    except: pass

    conn.commit()
    conn.close()

def create_user(username, password):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hash_password(password))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def validate_user(username, password):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, bio, avatar_base64, is_banned FROM users WHERE username=? AND password=?",
        (username, hash_password(password))
    )
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def update_user_profile(user_id, bio, avatar_base64, password=None, username=None):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        if username:
            cursor.execute("UPDATE users SET username=? WHERE id=?", (username, user_id))
        cursor.execute("UPDATE users SET bio=?, avatar_base64=? WHERE id=?", (bio, avatar_base64, user_id))
        if password and password.strip():
            cursor.execute("UPDATE users SET password=? WHERE id=?", (hash_password(password), user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_profile(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, bio, avatar_base64, is_banned FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_all_users():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, is_banned FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

def set_user_ban(user_id, is_banned):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned=? WHERE id=?", (int(is_banned), user_id))
    conn.commit()
    conn.close()

def create_room(name, creator_id, password='', avatar_base64=''):
    code = str(uuid.uuid4())[:8].upper()
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO rooms (name, code, creator_id, password, avatar_base64) VALUES (?, ?, ?, ?, ?)",
        (name, code, creator_id, password, avatar_base64)
    )
    room_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO room_members (room_id, user_id) VALUES (?, ?)",
        (room_id, creator_id)
    )
    conn.commit()
    conn.close()
    return {"id": room_id, "name": name, "code": code, "creator_id": creator_id, "has_password": bool(password), "avatar_base64": avatar_base64}

def update_room_settings(room_id, name, password, avatar_base64):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE rooms SET name=?, password=?, avatar_base64=? WHERE id=?",
        (name, password, avatar_base64, room_id)
    )
    conn.commit()
    conn.close()

def join_room(code, user_id, provided_password=''):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, creator_id, password, avatar_base64 FROM rooms WHERE code=?", (code,))
    room = cursor.fetchone()
    if not room:
        conn.close()
        return None, "Room code not found."
    
    if room["password"] and room["password"] != provided_password:
        conn.close()
        return None, "Incorrect room password."
    
    try:
        cursor.execute(
            "INSERT INTO room_members (room_id, user_id) VALUES (?, ?)",
            (room["id"], user_id)
        )
        conn.commit()
        room_dict = dict(room)
        room_dict["has_password"] = bool(room_dict["password"])
        del room_dict["password"]
        return room_dict, "Success"
    except sqlite3.IntegrityError:
        room_dict = dict(room)
        room_dict["has_password"] = bool(room_dict["password"])
        del room_dict["password"]
        return room_dict, "Already a member"
    finally:
        conn.close()

def get_user_rooms(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.id, r.name, r.code, r.creator_id, r.avatar_base64,
               CASE WHEN r.password != '' THEN 1 ELSE 0 END as has_password
        FROM rooms r
        JOIN room_members rm ON r.id = rm.room_id
        WHERE rm.user_id = ?
    ''', (user_id,))
    rooms = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rooms

def get_all_rooms():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, code, creator_id FROM rooms")
    rooms = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rooms

def get_room_members(room_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.bio, u.avatar_base64
        FROM users u
        JOIN room_members rm ON u.id = rm.user_id
        WHERE rm.room_id = ?
    ''', (room_id,))
    members = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return members

def save_message(room_id, sender_id, content):
    timestamp = datetime.now().isoformat()
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (room_id, sender_id, content, timestamp, status) VALUES (?, ?, ?, ?, 'delivered')",
        (room_id, sender_id, content, timestamp)
    )
    msg_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": msg_id, "room_id": room_id, "sender_id": sender_id, "content": content, "timestamp": timestamp, "status": "delivered"}

def mark_room_messages_read(room_id, reader_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE messages SET status='read' WHERE room_id=? AND sender_id != ? AND status='delivered'", (room_id, reader_id))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

def get_room_history(room_id, limit=100):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.id, m.room_id, m.sender_id, u.username, u.avatar_base64, m.content, m.timestamp, m.status
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.room_id = ?
        ORDER BY m.timestamp ASC LIMIT ?
    ''', (room_id, limit))
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return history

def remove_user_from_room(room_id, user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM room_members WHERE room_id=? AND user_id=?", (room_id, user_id))
    conn.commit()
    conn.close()

def delete_room(room_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE room_id=?", (room_id,))
    cursor.execute("DELETE FROM room_members WHERE room_id=?", (room_id,))
    cursor.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    conn.commit()
    conn.close()