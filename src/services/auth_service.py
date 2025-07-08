import os
import sqlite3
import hashlib
from typing import Dict, Any
from config.settings import BASE_DIR

# Database path for users
DB_PATH = os.path.join(BASE_DIR, 'data', 'app.db')

def get_db_conn():
    """Get database connection for user management"""
    return sqlite3.connect(DB_PATH)

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_users_table():
    """Create users table if it doesn't exist"""
    conn = get_db_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('superadmin', 'admin'))
    )''')
    conn.commit()
    conn.close()

def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    """Authenticate user login"""
    if not username or not password:
        return {"success": False, "message": "Username and password required"}
    
    conn = get_db_conn()
    c = conn.cursor()
    c.execute('SELECT password, role FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    
    if row and row[0] == hash_password(password):
        return {"success": True, "role": row[1]}
    return {"success": False, "message": "Invalid credentials"}

def add_admin_user(username: str, password: str, role: str = 'admin') -> Dict[str, Any]:
    """Add a new admin user"""
    if not username or not password:
        return {"success": False, "message": "Username and password required"}
    if role not in ('admin', 'superadmin'):
        return {"success": False, "message": "Invalid role"}
    
    try:
        conn = get_db_conn()
        c = conn.cursor()
        c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                  (username, hash_password(password), role))
        conn.commit()
        conn.close()
        return {"success": True, "message": f"Admin '{username}' added."}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "Username already exists."}

def delete_admin_user(username: str) -> Dict[str, Any]:
    """Delete an admin user"""
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    deleted = c.rowcount
    conn.close()
    
    if deleted:
        return {"success": True, "message": f"Admin '{username}' deleted."}
    else:
        return {"success": False, "message": f"Admin '{username}' not found."}

def list_admin_users() -> Dict[str, Any]:
    """List all admin and superadmin users"""
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT username, role FROM users WHERE role IN ('admin', 'superadmin') ORDER BY role DESC, username ASC")
    admins = [{"username": row[0], "role": row[1]} for row in c.fetchall()]
    conn.close()
    return {"success": True, "admins": admins}

# Initialize the users table when module is imported
create_users_table()
