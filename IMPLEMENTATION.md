# Flask ToDo App - Feature Implementation Guide

## Overview
This document details the complete implementation of Task Descriptions, Search, Filters, and Sorting features for the Flask ToDo CRUD app.

---

## 1. Task Descriptions & Metadata

### Database Schema Extensions

```python
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,                    -- NEW: Task description
    priority TEXT DEFAULT 'medium',      -- NEW: Priority (low, medium, high)
    category TEXT DEFAULT 'personal',
    completed BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date DATE,                       -- NEW: Due date
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- NEW: Auto-updated timestamp
)
```

### Database Indexes (Performance Optimization)

```python
CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(completed)
CREATE INDEX IF NOT EXISTS idx_todos_priority ON todos(priority)
CREATE INDEX IF NOT EXISTS idx_todos_due_date ON todos(due_date)
CREATE INDEX IF NOT EXISTS idx_todos_category ON todos(category)
```

### Migration Strategy

Safe migrations with try-except blocks to handle existing tables:

```python
# Add due_date column if it doesn't exist
try:
    cursor.execute('ALTER TABLE todos ADD COLUMN due_date DATE')
    conn.commit()
except:
    pass  # Column already exists

# Add updated_at column if it doesn't exist
try:
    cursor.execute('ALTER TABLE todos ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    conn.commit()
except:
    pass
```

### Backend Routes

#### Add Task
```python
@app.route('/add', methods=['POST'])
def add_todo():
    title = request.form.get('title')
    description = request.form.get('description', '')
    priority = request.form.get('priority', 'medium')
    category = request.form.get('category', 'personal')
    due_date = request.form.get('due_date', None)
    
    cursor.execute('''INSERT INTO todos (title, description, priority, category, due_date, updated_at) 
                      VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''', 
                   (title, description, priority, category, due_date if due_date else None))
```

#### Edit Task
```python
@app.route('/edit/<int:todo_id>', methods=['POST'])
def edit_todo(todo_id):
    title = request.form.get('title')
    description = request.form.get('description', '')
    priority = request.form.get('priority', 'medium')
    category = request.form.get('category', 'personal')
    due_date = request.form.get('due_date', None)
    
    cursor.execute('''UPDATE todos SET title = ?, description = ?, priority = ?, 
                      category = ?, due_date = ?, updated_at = CURRENT_TIMESTAMP 
                      WHERE id = ?''',
                   (title, description, priority, category, due_date if due_date else None, todo_id))
```

#### Toggle Task (with auto-update)
```python
@app.route('/toggle/<int:todo_id>')
def toggle_todo(todo_id):
    cursor.execute('UPDATE todos SET completed = NOT completed, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (todo_id,))
```

### Frontend Integration

#### Add Task Form
```html
<!-- Priority Radio Buttons (existing UI) -->
<div class="priority-group">
    <div class="priority-option">
        <input type="radio" name="priority" value="low" id="p-low">
        <label for="p-low" class="priority-label low">Low</label>
    </div>
    <div class="priority-option">
        <input type="radio" name="priority" value="medium" id="p-med" checked>
        <label for="p-med" class="priority-label medium">Med</label>
    </div>
    <div class="priority-option">
        <input type="radio" name="priority" value="high" id="p-high">
        <label for="p-high" class="priority-label high">High</label>
    </div>
</div>

<!-- Due Date Input -->
<input type="date" name="due_date" class="input">

<!-- Description Textarea (existing UI) -->
<textarea name="description" class="input" placeholder="Add details..."></textarea>
```

#### Task Display
```html
<div class="task-content">
    <div class="task-title">{{ todo['title'] }}</div>
    
    <!-- Description (only if present) -->
    {% if todo['description'] %}
    <div class="task-description">{{ todo['description'] }}</div>
    {% endif %}
    
    <!-- Metadata badges -->
    <div class="task-meta">
        <span class="task-badge badge-category">{{ todo['category']|capitalize }}</span>
        <span class="task-badge badge-priority-{{ todo['priority'] or 'medium' }}">
            {{ todo['priority']|capitalize }}
        </span>
        {% if todo['due_date'] %}
        <span class="task-date">📅 Due: {{ todo['due_date'] }}</span>
        {% endif %}
        <span class="task-date">Created: {{ todo['created_at'][:10] }}</span>
    </div>
</div>
```

---

## 2. Search Functionality

### Backend Implementation

```python
@app.route('/')
def index():
    search_query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    query = 'SELECT * FROM todos WHERE 1=1'
    params = []
    
    # Apply search filter
    if search_query:
        query += ' AND (title LIKE ? OR description LIKE ?)'
        search_pattern = f'%{search_query}%'
        params.extend([search_pattern, search_pattern])
    
    # ... other filters and sorting ...
    
    # Apply pagination
    query += ' LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    
    cursor.execute(query, params)
    todos = cursor.fetchall()
    
    # Get total count for pagination
    count_query = 'SELECT COUNT(*) FROM todos WHERE 1=1'
    # ... apply same filters to count query ...
    cursor.execute(count_query, count_params)
    total_count = cursor.fetchone()[0]
    total_pages = (total_count + per_page - 1) // per_page
```

### Frontend Integration

```html
<!-- Search Form (existing UI) -->
<form method="GET" action="/">
    <div class="form-group">
        <input type="search" name="q" class="input" 
               placeholder="🔍 Search tasks..." 
               value="{{ search_query or '' }}">
    </div>
    <!-- Hidden fields to preserve current filters -->
    <input type="hidden" name="category" value="{{ current_category }}">
    <input type="hidden" name="status" value="{{ filter_status }}">
    <input type="hidden" name="priority" value="{{ filter_priority }}">
    <input type="hidden" name="due" value="{{ filter_due }}">
    <input type="hidden" name="sort" value="{{ sort_by }}">
</form>
```

---

## 3. Filters and Sorting

### Backend Query Builder

```python
@app.route('/')
def index():
    # Get filter parameters
    filter_status = request.args.get('status', 'all')      # all, active, completed
    filter_priority = request.args.get('priority', 'all')  # all, low, medium, high
    filter_due = request.args.get('due', 'all')            # all, overdue, today, week
    sort_by = request.args.get('sort', 'default')          # default, due_date, created_at, priority, alpha
    
    query = 'SELECT * FROM todos WHERE 1=1'
    params = []
    
    # Status Filter
    if filter_status == 'active':
        query += ' AND completed = 0'
    elif filter_status == 'completed':
        query += ' AND completed = 1'
    
    # Priority Filter
    if filter_priority != 'all':
        query += ' AND priority = ?'
        params.append(filter_priority)
    
    # Due Date Filter
    if filter_due == 'overdue':
        query += ' AND due_date IS NOT NULL AND due_date < date("now")'
    elif filter_due == 'today':
        query += ' AND due_date = date("now")'
    elif filter_due == 'week':
        query += ' AND due_date IS NOT NULL AND due_date >= date("now") AND due_date <= date("now", "+7 days")'
    
    # Sorting
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
```

### Frontend Integration

```html
<!-- Filter Dropdowns (existing UI) -->
<div style="display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap;">
    <!-- Status Filter -->
    <select id="status-filter" class="select" onchange="applyFilters()">
        <option value="all" {% if filter_status == 'all' %}selected{% endif %}>All Status</option>
        <option value="active" {% if filter_status == 'active' %}selected{% endif %}>Active</option>
        <option value="completed" {% if filter_status == 'completed' %}selected{% endif %}>Completed</option>
    </select>
    
    <!-- Priority Filter -->
    <select id="priority-filter" class="select" onchange="applyFilters()">
        <option value="all" {% if filter_priority == 'all' %}selected{% endif %}>All Priorities</option>
        <option value="high" {% if filter_priority == 'high' %}selected{% endif %}>High</option>
        <option value="medium" {% if filter_priority == 'medium' %}selected{% endif %}>Medium</option>
        <option value="low" {% if filter_priority == 'low' %}selected{% endif %}>Low</option>
    </select>
    
    <!-- Due Date Filter -->
    <select id="due-filter" class="select" onchange="applyFilters()">
        <option value="all" {% if filter_due == 'all' %}selected{% endif %}>All Due Dates</option>
        <option value="overdue" {% if filter_due == 'overdue' %}selected{% endif %}>Overdue</option>
        <option value="today" {% if filter_due == 'today' %}selected{% endif %}>Due Today</option>
        <option value="week" {% if filter_due == 'week' %}selected{% endif %}>Due This Week</option>
    </select>
    
    <!-- Sort Dropdown -->
    <select id="sort-by" class="select" onchange="applyFilters()">
        <option value="default" {% if sort_by == 'default' %}selected{% endif %}>Sort: Default</option>
        <option value="due_date" {% if sort_by == 'due_date' %}selected{% endif %}>Sort: Due Date</option>
        <option value="created_at" {% if sort_by == 'created_at' %}selected{% endif %}>Sort: Created</option>
        <option value="priority" {% if sort_by == 'priority' %}selected{% endif %}>Sort: Priority</option>
        <option value="alpha" {% if sort_by == 'alpha' %}selected{% endif %}>Sort: A-Z</option>
    </select>
</div>

<script>
function applyFilters() {
    const status = document.getElementById('status-filter').value;
    const priority = document.getElementById('priority-filter').value;
    const due = document.getElementById('due-filter').value;
    const sort = document.getElementById('sort-by').value;
    
    const params = new URLSearchParams(window.location.search);
    params.set('status', status);
    params.set('priority', priority);
    params.set('due', due);
    params.set('sort', sort);
    params.delete('page'); // Reset to page 1 when filters change
    
    window.location.href = '?' + params.toString();
}
</script>
```

---

## 4. Pagination

### Implementation

```html
{% if total_pages > 1 %}
<div style="display: flex; justify-content: center; gap: 8px; margin-top: 24px;">
    {% if page > 1 %}
    <a href="/?category={{ current_category }}&status={{ filter_status }}&priority={{ filter_priority }}&due={{ filter_due }}&sort={{ sort_by }}&page={{ page - 1 }}{% if search_query %}&q={{ search_query }}{% endif %}" 
       class="btn btn-secondary btn-sm">Previous</a>
    {% endif %}
    
    <span style="padding: 6px 12px; color: var(--text-secondary); font-size: 13px;">
        Page {{ page }} of {{ total_pages }}
    </span>
    
    {% if page < total_pages %}
    <a href="/?category={{ current_category }}&status={{ filter_status }}&priority={{ filter_priority }}&due={{ filter_due }}&sort={{ sort_by }}&page={{ page + 1 }}{% if search_query %}&q={{ search_query }}{% endif %}" 
       class="btn btn-secondary btn-sm">Next</a>
    {% endif %}
</div>
{% endif %}
```

---

## 5. Key Implementation Features

### ✅ No UI Changes
- All features use existing CSS classes and styling
- No new layout elements added
- Only minimal Jinja variable insertions for data display

### ✅ Safe Database Migrations
- Try-except blocks prevent errors on existing tables
- Default values for all new columns
- Backwards compatible

### ✅ Clean Query Builder
- SQL injection protection via parameterized queries
- Modular filter application
- Efficient database indexing

### ✅ Filter State Preservation
- Search form preserves all filters via hidden inputs
- Category links maintain active filters
- Pagination links include all current filter parameters

### ✅ Professional Git Workflow
- Feature branches: `feature/task-descriptions-and-metadata`, `feature/search-tasks`, `feature/filters-and-sorting`
- Clean commits per feature
- Merged through `dev` branch to `main`
- Tagged release: v0.1.0

---

## 6. Testing Guide

### Test Task Creation
1. Fill in title, select priority, set due date, add description
2. Submit form
3. Verify task displays with all metadata

### Test Search
1. Enter search term in search box
2. Verify results match title OR description
3. Verify pagination works with search

### Test Filters
1. Select status filter (active/completed)
2. Select priority filter (high/medium/low)
3. Select due date filter (overdue/today/week)
4. Verify correct tasks displayed

### Test Sorting
1. Sort by due date - verify chronological order
2. Sort by priority - verify high → medium → low
3. Sort by created date - verify newest first
4. Sort alphabetically - verify A-Z order

### Test Filter Preservation
1. Apply multiple filters
2. Navigate to different category
3. Verify filters remain active
4. Use pagination
5. Verify filters remain active

---

## 7. Docker Deployment

### Build and Push
```bash
docker build -t a3yyad/todo-saas:0.1.0 .
docker tag a3yyad/todo-saas:0.1.0 a3yyad/todo-saas:latest
docker push a3yyad/todo-saas:0.1.0
docker push a3yyad/todo-saas:latest
```

### Run Locally
```bash
docker run -d -p 5000:5000 -v todo-data:/app/data a3yyad/todo-saas:0.1.0
```

---

## Summary

All features implemented successfully:
- ✅ Task descriptions, priority, due dates, updated_at timestamps
- ✅ Full-text search across titles and descriptions
- ✅ Comprehensive filtering by status, priority, and due date ranges
- ✅ Multiple sorting options
- ✅ Pagination with filter preservation
- ✅ Safe database migrations
- ✅ No UI/layout changes
- ✅ Clean, production-ready code
- ✅ Professional Git workflow with feature branches
