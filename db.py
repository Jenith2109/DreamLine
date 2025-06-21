import sqlite3

def init_db():
    conn = sqlite3.connect('dip_users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            sentiment TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Add custom_prompt and custom_agent_name columns if they don't exist
    try:
        c.execute('ALTER TABLE users ADD COLUMN custom_agent_name TEXT')
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        c.execute('ALTER TABLE users ADD COLUMN custom_prompt TEXT')
    except sqlite3.OperationalError:
        pass # Column already exists

    conn.commit()
    conn.close()

def get_or_create_user(username):
    conn = sqlite3.connect('dip_users.db')
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    if user:
        return user[0]
    c.execute('INSERT INTO users (username) VALUES (?)', (username,))
    conn.commit()
    return c.lastrowid
