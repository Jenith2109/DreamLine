from textblob import TextBlob
import sqlite3

def save_message(user_id, message):
    sentiment = TextBlob(message).sentiment.polarity
    emotion = "positive" if sentiment > 0.1 else "negative" if sentiment < -0.1 else "neutral"
    
    conn = sqlite3.connect('dip_users.db')
    c = conn.cursor()
    c.execute('INSERT INTO memories (user_id, message, sentiment) VALUES (?, ?, ?)', (user_id, message, emotion))
    conn.commit()
    conn.close()

def get_memory(user_id):
    conn = sqlite3.connect('dip_users.db')
    c = conn.cursor()
    c.execute('SELECT message FROM memories WHERE user_id = ? ORDER BY id ASC', (user_id,))
    memory = "\n".join([row[0] for row in c.fetchall()])
    conn.close()
    return memory
