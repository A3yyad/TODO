from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Database setup with category field
def init_db():
    conn = sqlite3.connect('/app/data/todo.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'medium',
            category TEXT DEFAULT 'personal',
            completed BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add category column if it doesn't exist (for migration)
    try:
        cursor.execute('ALTER TABLE todos ADD COLUMN category TEXT DEFAULT "personal"')
        conn.commit()
    except:
        pass  # Column already exists
    
    conn.close()

# Initialize database on startup
init_db()

# CREATE - Add new todo
@app.route('/add', methods=['POST'])
def add_todo():
    title = request.form.get('title')
    description = request.form.get('description', '')
    priority = request.form.get('priority', 'medium')
    category = request.form.get('category', 'personal')
    
    conn = sqlite3.connect('/app/data/todo.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO todos (title, description, priority, category) VALUES (?, ?, ?, ?)', 
                   (title, description, priority, category))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

# READ - Get all todos
@app.route('/')
def index():
    filter_category = request.args.get('category', 'all')
    
    conn = sqlite3.connect('/app/data/todo.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if filter_category == 'all':
        cursor.execute('SELECT * FROM todos ORDER BY created_at DESC')
    else:
        cursor.execute('SELECT * FROM todos WHERE category = ? ORDER BY created_at DESC', (filter_category,))
    
    todos = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', todos=todos, current_category=filter_category)

# UPDATE - Toggle completion status
@app.route('/toggle/<int:todo_id>')
def toggle_todo(todo_id):
    conn = sqlite3.connect('/app/data/todo.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE todos SET completed = NOT completed WHERE id = ?', (todo_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

# UPDATE - Edit todo
@app.route('/edit/<int:todo_id>', methods=['POST'])
def edit_todo(todo_id):
    title = request.form.get('title')
    description = request.form.get('description', '')
    priority = request.form.get('priority', 'medium')
    category = request.form.get('category', 'personal')
    
    conn = sqlite3.connect('/app/data/todo.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE todos SET title = ?, description = ?, priority = ?, category = ? WHERE id = ?',
                   (title, description, priority, category, todo_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

# DELETE - Remove todo
@app.route('/delete/<int:todo_id>')
def delete_todo(todo_id):
    conn = sqlite3.connect('/app/data/todo.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)