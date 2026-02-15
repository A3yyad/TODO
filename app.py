from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date DATE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add category column if it doesn't exist (migration)
    try:
        cursor.execute('ALTER TABLE todos ADD COLUMN category TEXT DEFAULT "personal"')
        conn.commit()
    except:
        pass
    
    # Add due_date column if it doesn't exist (migration)
    try:
        cursor.execute('ALTER TABLE todos ADD COLUMN due_date DATE')
        conn.commit()
    except:
        pass
    
    # Add updated_at column if it doesn't exist (migration)
    try:
        cursor.execute('ALTER TABLE todos ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        conn.commit()
    except:
        pass
    
    # Create indexes for better query performance
    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(completed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_todos_priority ON todos(priority)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_todos_due_date ON todos(due_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_todos_category ON todos(category)')
        conn.commit()
    except:
        pass
    
    conn.close()

init_db()

@app.route('/add', methods=['POST'])
def add_todo():
    title = request.form.get('title')
    description = request.form.get('description', '')
    priority = request.form.get('priority', 'medium')
    category = request.form.get('category', 'personal')
    due_date = request.form.get('due_date', None)
    
    conn = sqlite3.connect('/app/data/todo.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO todos (title, description, priority, category, due_date, updated_at) 
                      VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''', 
                   (title, description, priority, category, due_date if due_date else None))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route('/')
def index():
    filter_category = request.args.get('category', 'all')
    search_query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # New filters
    filter_status = request.args.get('status', 'all')  # all, active, completed
    filter_priority = request.args.get('priority', 'all')  # all, low, medium, high
    filter_due = request.args.get('due', 'all')  # all, overdue, today, week
    sort_by = request.args.get('sort', 'default')  # default, due_date, created_at, priority, alpha
    
    conn = sqlite3.connect('/app/data/todo.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Build query based on filters and search
    query = 'SELECT * FROM todos WHERE 1=1'
    params = []
    
    # Apply category filter
    if filter_category != 'all':
        query += ' AND category = ?'
        params.append(filter_category)
    
    # Apply status filter
    if filter_status == 'active':
        query += ' AND completed = 0'
    elif filter_status == 'completed':
        query += ' AND completed = 1'
    
    # Apply priority filter
    if filter_priority != 'all':
        query += ' AND priority = ?'
        params.append(filter_priority)
    
    # Apply due date filter
    if filter_due == 'overdue':
        query += ' AND due_date IS NOT NULL AND due_date < date("now")'
    elif filter_due == 'today':
        query += ' AND due_date = date("now")'
    elif filter_due == 'week':
        query += ' AND due_date IS NOT NULL AND due_date >= date("now") AND due_date <= date("now", "+7 days")'
    
    # Apply search filter
    if search_query:
        query += ' AND (title LIKE ? OR description LIKE ?)'
        search_pattern = f'%{search_query}%'
        params.extend([search_pattern, search_pattern])
    
    # Apply sorting
    if sort_by == 'due_date':
        query += ' ORDER BY due_date ASC NULLS LAST, created_at DESC'
    elif sort_by == 'created_at':
        query += ' ORDER BY created_at DESC'
    elif sort_by == 'priority':
        query += ' ORDER BY CASE priority WHEN "high" THEN 1 WHEN "medium" THEN 2 WHEN "low" THEN 3 END, created_at DESC'
    elif sort_by == 'alpha':
        query += ' ORDER BY title COLLATE NOCASE ASC'
    else:  # default
        query += ' ORDER BY completed ASC, created_at DESC'
    
    # Apply pagination
    query += ' LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    
    cursor.execute(query, params)
    todos = cursor.fetchall()
    
    # Get total count for pagination
    count_query = 'SELECT COUNT(*) FROM todos WHERE 1=1'
    count_params = []
    
    if filter_category != 'all':
        count_query += ' AND category = ?'
        count_params.append(filter_category)
    
    if filter_status == 'active':
        count_query += ' AND completed = 0'
    elif filter_status == 'completed':
        count_query += ' AND completed = 1'
    
    if filter_priority != 'all':
        count_query += ' AND priority = ?'
        count_params.append(filter_priority)
    
    if filter_due == 'overdue':
        count_query += ' AND due_date IS NOT NULL AND due_date < date("now")'
    elif filter_due == 'today':
        count_query += ' AND due_date = date("now")'
    elif filter_due == 'week':
        count_query += ' AND due_date IS NOT NULL AND due_date >= date("now") AND due_date <= date("now", "+7 days")'
    
    if search_query:
        count_query += ' AND (title LIKE ? OR description LIKE ?)'
        count_params.extend([search_pattern, search_pattern])
    
    cursor.execute(count_query, count_params)
    total_count = cursor.fetchone()[0]
    total_pages = (total_count + per_page - 1) // per_page
    
    conn.close()
    
    return render_template('index.html', 
                         todos=todos, 
                         current_category=filter_category,
                         search_query=search_query,
                         page=page,
                         total_pages=total_pages,
                         filter_status=filter_status,
                         filter_priority=filter_priority,
                         filter_due=filter_due,
                         sort_by=sort_by)

@app.route('/toggle/<int:todo_id>')
def toggle_todo(todo_id):
    conn = sqlite3.connect('/app/data/todo.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE todos SET completed = NOT completed, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (todo_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route('/edit/<int:todo_id>', methods=['POST'])
def edit_todo(todo_id):
    title = request.form.get('title')
    description = request.form.get('description', '')
    priority = request.form.get('priority', 'medium')
    category = request.form.get('category', 'personal')
    due_date = request.form.get('due_date', None)
    
    conn = sqlite3.connect('/app/data/todo.db')
    cursor = conn.cursor()
    cursor.execute('''UPDATE todos SET title = ?, description = ?, priority = ?, category = ?, due_date = ?, updated_at = CURRENT_TIMESTAMP 
                      WHERE id = ?''',
                   (title, description, priority, category, due_date if due_date else None, todo_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

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