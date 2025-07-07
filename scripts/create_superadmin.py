import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '../data/app.db')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_superadmin():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('superadmin', 'admin'))
    )''')
    try:
        c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                  ('superadmin', hash_password('superadmin@123'), 'superadmin'))
        print('Superadmin user created.')
    except sqlite3.IntegrityError:
        print('Superadmin user already exists.')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_superadmin()
