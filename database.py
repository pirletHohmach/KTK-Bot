import sqlite3


def init_db():
    conn = sqlite3.connect('glados.db')
    cursor = conn.cursor()

    # Existing users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                     user_id INTEGER PRIMARY KEY,
                     username TEXT,
                     first_name TEXT,
                     last_name TEXT,
                     group_id TEXT)
                     ''')

    # New teachers table
    cursor.execute('''CREATE TABLE IF NOT EXISTS teachers (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT UNIQUE NOT NULL)
                     ''')

    # New ratings table
    cursor.execute('''CREATE TABLE IF NOT EXISTS teacher_ratings (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     teacher_id INTEGER,
                     user_id INTEGER,
                     rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY(teacher_id) REFERENCES teachers(id),
                     FOREIGN KEY(user_id) REFERENCES users(user_id),
                     UNIQUE(teacher_id, user_id))
                     ''')

    # New table for tracking last schedule check
    cursor.execute('''CREATE TABLE IF NOT EXISTS schedule_checks (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     date TEXT UNIQUE,
                     last_hash TEXT)
                     ''')

    conn.commit()
    cursor.close()
    conn.close()

def add_teacher(name):
    conn = sqlite3.connect('glados.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT OR IGNORE INTO teachers (name) VALUES (?)', (name,))
        conn.commit()
        return cursor.lastrowid or cursor.execute('SELECT id FROM teachers WHERE name = ?', (name,)).fetchone()[0]
    finally:
        cursor.close()
        conn.close()


def rate_teacher(user_id, teacher_name, rating):
    if not 1 <= rating <= 5:
        return False, "Rating must be between 1 and 5"

    conn = sqlite3.connect('glados.db')
    cursor = conn.cursor()
    try:
        teacher_id = add_teacher(teacher_name)
        cursor.execute('''INSERT OR REPLACE INTO teacher_ratings 
                         (teacher_id, user_id, rating) VALUES (?, ?, ?)''',
                       (teacher_id, user_id, rating))
        conn.commit()
        return True, "Rating submitted successfully"
    except Exception as e:
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def get_teacher_rating(teacher_name):
    conn = sqlite3.connect('glados.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT 
                t.name,
                COUNT(tr.rating) as total_ratings,
                ROUND(AVG(tr.rating), 2) as average_rating
            FROM teachers t
            LEFT JOIN teacher_ratings tr ON t.id = tr.teacher_id
            WHERE t.name = ?
            GROUP BY t.id
        ''', (teacher_name,))
        result = cursor.fetchone()
        if result:
            return {
                'name': result[0],
                'total_ratings': result[1],
                'average_rating': result[2]
            }
        return None
    finally:
        cursor.close()
        conn.close()

def update_schedule_check(date, schedule_hash):
    conn = sqlite3.connect('glados.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''INSERT OR REPLACE INTO schedule_checks (date, last_hash) 
                         VALUES (?, ?)''', (date, schedule_hash))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def get_last_schedule_hash(date):
    conn = sqlite3.connect('glados.db')
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT last_hash FROM schedule_checks WHERE date = ?', (date,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        conn.close()

def get_all_user_ids():
    conn = sqlite3.connect('glados.db')
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT user_id FROM users')
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()

#Добавление пользователя в базу данных
def add_user(user_id, username, first_name, last_name, group_id):
    conn = sqlite3.connect('glados.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO users (
                    user_id, 
                    username, 
                    first_name,
                    last_name,
                    group_id)
    VALUES (?, ?, ?, ?, ?)''',
(user_id, username, first_name, last_name, group_id))
    conn.commit()
    cursor.close()
    conn.close()


#Обновляем группу
def update_user_group(user_id, group_id):
    conn = sqlite3.connect('glados.db')
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE users SET group_id = ? WHERE user_id = ?''',
(group_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()


#Проверка на чела есть ли он в базе данных
def check_user(user_id):
    conn = sqlite3.connect('glados.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT user_id FROM users WHERE user_id = ?''',
(user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user is not None  # Возвращаем True, если пользователь существует, иначе False


def get_user_group(user_id):
    conn = sqlite3.connect('glados.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT group_id FROM users WHERE user_id = ?''',
(user_id,))
    result = cursor.fetchone()
    group = result[0] if result else None

    cursor.close()
    conn.close()
    return group