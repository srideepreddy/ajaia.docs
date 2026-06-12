"""
AjaiaDocs — Flask backend
Serves the frontend at / and the REST API at /api/*
"""
import sqlite3
import uuid
import json
import os
import re
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, g

app = Flask(__name__, static_folder='frontend_dist', static_url_path='')

DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'data.db'))

# ── Database ───────────────────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    """Create tables and seed demo users."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'Untitled',
            content TEXT NOT NULL DEFAULT '',
            owner_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (owner_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS document_shares (
            doc_id TEXT NOT NULL,
            shared_with_id TEXT NOT NULL,
            granted_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (doc_id, shared_with_id),
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (shared_with_id) REFERENCES users(id)
        );
    """)
    # Seed demo users
    for uid, email, name, token in [
        ('user-alice', 'alice@test.com', 'Alice Chen',     'token-alice-123'),
        ('user-bob',   'bob@test.com',   'Bob Martinez',   'token-bob-456'),
        ('user-carol', 'carol@test.com', 'Carol Singh',    'token-carol-789'),
    ]:
        con.execute(
            'INSERT OR IGNORE INTO users (id,email,name,token) VALUES (?,?,?,?)',
            (uid, email, name, token)
        )
    # Seed welcome doc for alice
    exists = con.execute('SELECT id FROM documents WHERE id=?', ('doc-sample-1',)).fetchone()
    if not exists:
        welcome = json.dumps({
            "type": "doc",
            "content": [
                {"type":"heading","attrs":{"level":1},"content":[{"type":"text","text":"Welcome to AjaiaDocs"}]},
                {"type":"paragraph","content":[{"type":"text","text":"This is a collaborative document editor. Use the toolbar to format text, upload .txt or .md files, and share documents with teammates."}]},
                {"type":"heading","attrs":{"level":2},"content":[{"type":"text","text":"Getting started"}]},
                {"type":"bulletList","content":[
                    {"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","marks":[{"type":"bold"}],"text":"Create"},{"type":"text","text":" a new document with the + button"}]}]},
                    {"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","marks":[{"type":"bold"}],"text":"Upload"},{"type":"text","text":" a .txt or .md file to import it"}]}]},
                    {"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","marks":[{"type":"bold"}],"text":"Share"},{"type":"text","text":" any document you own with other users"}]}]},
                    {"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","text":"Demo accounts: alice@test.com, bob@test.com, carol@test.com"}]}]}
                ]}
            ]
        })
        con.execute(
            'INSERT INTO documents (id,title,content,owner_id) VALUES (?,?,?,?)',
            ('doc-sample-1', 'Welcome to AjaiaDocs', welcome, 'user-alice')
        )
    con.commit()
    con.close()

# ── Auth middleware ────────────────────────────────────────────────────────────

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Missing token'}), 401
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE token=?', (token,)).fetchone()
        if not user:
            return jsonify({'error': 'Invalid token'}), 401
        g.user = dict(user)
        return f(*args, **kwargs)
    return wrapper

def row(r):
    return dict(r) if r else None

def rows(rs):
    return [dict(r) for r in rs]

# ── Auth routes ────────────────────────────────────────────────────────────────

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email required'}), 400
    db = get_db()
    user = db.execute('SELECT id,email,name,token FROM users WHERE lower(email)=?', (email,)).fetchone()
    if not user:
        return jsonify({'error': 'No user with that email. Try alice@test.com, bob@test.com, or carol@test.com'}), 404
    u = dict(user)
    return jsonify({'user': {'id': u['id'], 'email': u['email'], 'name': u['name']}, 'token': u['token']})

@app.route('/api/auth/me')
@require_auth
def me():
    return jsonify({'id': g.user['id'], 'email': g.user['email'], 'name': g.user['name']})

# ── Users ──────────────────────────────────────────────────────────────────────

@app.route('/api/users')
@require_auth
def list_users():
    db = get_db()
    users = rows(db.execute('SELECT id,email,name FROM users WHERE id!=?', (g.user['id'],)).fetchall())
    return jsonify(users)

# ── Documents ──────────────────────────────────────────────────────────────────

@app.route('/api/documents')
@require_auth
def list_documents():
    db = get_db()
    owned = rows(db.execute("""
        SELECT id,title,owner_id,created_at,updated_at,'owned' as relation
        FROM documents WHERE owner_id=? ORDER BY updated_at DESC
    """, (g.user['id'],)).fetchall())

    shared = rows(db.execute("""
        SELECT d.id,d.title,d.owner_id,d.created_at,d.updated_at,
               'shared' as relation, u.name as owner_name, u.email as owner_email
        FROM documents d
        JOIN document_shares ds ON ds.doc_id=d.id
        JOIN users u ON u.id=d.owner_id
        WHERE ds.shared_with_id=? ORDER BY d.updated_at DESC
    """, (g.user['id'],)).fetchall())

    return jsonify({'owned': owned, 'shared': shared})

@app.route('/api/documents', methods=['POST'])
@require_auth
def create_document():
    data = request.get_json() or {}
    title = data.get('title', 'Untitled')
    content = data.get('content', '')
    if not isinstance(content, str):
        content = json.dumps(content)
    doc_id = str(uuid.uuid4())
    db = get_db()
    db.execute('INSERT INTO documents (id,title,content,owner_id) VALUES (?,?,?,?)',
               (doc_id, title, content, g.user['id']))
    db.commit()
    doc = row(db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone())
    return jsonify(doc), 201

@app.route('/api/documents/<doc_id>')
@require_auth
def get_document(doc_id):
    db = get_db()
    doc = row(db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone())
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    is_owner = doc['owner_id'] == g.user['id']
    is_shared = db.execute(
        'SELECT 1 FROM document_shares WHERE doc_id=? AND shared_with_id=?',
        (doc_id, g.user['id'])
    ).fetchone()
    if not is_owner and not is_shared:
        return jsonify({'error': 'Access denied'}), 403
    owner = row(db.execute('SELECT id,name,email FROM users WHERE id=?', (doc['owner_id'],)).fetchone())
    shares = rows(db.execute("""
        SELECT u.id,u.name,u.email FROM document_shares ds
        JOIN users u ON u.id=ds.shared_with_id WHERE ds.doc_id=?
    """, (doc_id,)).fetchall())
    doc['owner'] = owner
    doc['shares'] = shares
    doc['relation'] = 'owned' if is_owner else 'shared'
    return jsonify(doc)

@app.route('/api/documents/<doc_id>', methods=['PUT'])
@require_auth
def update_document(doc_id):
    db = get_db()
    doc = row(db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone())
    if not doc:
        return jsonify({'error': 'Not found'}), 404
    if doc['owner_id'] != g.user['id']:
        return jsonify({'error': 'Only the owner can edit this document'}), 403
    data = request.get_json() or {}
    title = data.get('title', doc['title'])
    content = data.get('content', doc['content'])
    if not isinstance(content, str):
        content = json.dumps(content)
    db.execute("""
        UPDATE documents SET title=?,content=?,updated_at=datetime('now') WHERE id=?
    """, (title, content, doc_id))
    db.commit()
    return jsonify(row(db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone()))

@app.route('/api/documents/<doc_id>', methods=['DELETE'])
@require_auth
def delete_document(doc_id):
    db = get_db()
    doc = row(db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone())
    if not doc:
        return jsonify({'error': 'Not found'}), 404
    if doc['owner_id'] != g.user['id']:
        return jsonify({'error': 'Only the owner can delete'}), 403
    db.execute('DELETE FROM documents WHERE id=?', (doc_id,))
    db.commit()
    return jsonify({'success': True})

# ── Sharing ────────────────────────────────────────────────────────────────────

@app.route('/api/documents/<doc_id>/share', methods=['POST'])
@require_auth
def share_document(doc_id):
    db = get_db()
    doc = row(db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone())
    if not doc:
        return jsonify({'error': 'Not found'}), 404
    if doc['owner_id'] != g.user['id']:
        return jsonify({'error': 'Only the owner can share'}), 403
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email required'}), 400
    target = row(db.execute('SELECT * FROM users WHERE lower(email)=?', (email,)).fetchone())
    if not target:
        return jsonify({'error': f'No user found: {email}'}), 404
    if target['id'] == g.user['id']:
        return jsonify({'error': 'Cannot share with yourself'}), 400
    db.execute(
        'INSERT OR IGNORE INTO document_shares (doc_id,shared_with_id) VALUES (?,?)',
        (doc_id, target['id'])
    )
    db.commit()
    return jsonify({'success': True, 'sharedWith': {'id': target['id'], 'name': target['name'], 'email': target['email']}})

@app.route('/api/documents/<doc_id>/share/<user_id>', methods=['DELETE'])
@require_auth
def revoke_share(doc_id, user_id):
    db = get_db()
    doc = row(db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone())
    if not doc:
        return jsonify({'error': 'Not found'}), 404
    if doc['owner_id'] != g.user['id']:
        return jsonify({'error': 'Only the owner can revoke'}), 403
    db.execute('DELETE FROM document_shares WHERE doc_id=? AND shared_with_id=?', (doc_id, user_id))
    db.commit()
    return jsonify({'success': True})

# ── File upload ────────────────────────────────────────────────────────────────

def text_to_tiptap(text, filename):
    """Convert plain text / markdown to Tiptap JSON."""
    lines = text.split('\n')
    content_nodes = []
    for line in lines:
        if line.startswith('# '):
            content_nodes.append({'type':'heading','attrs':{'level':1},'content':[{'type':'text','text':line[2:]}]})
        elif line.startswith('## '):
            content_nodes.append({'type':'heading','attrs':{'level':2},'content':[{'type':'text','text':line[3:]}]})
        elif line.startswith('### '):
            content_nodes.append({'type':'heading','attrs':{'level':3},'content':[{'type':'text','text':line[4:]}]})
        else:
            para = {'type':'paragraph'}
            if line.strip():
                para['content'] = [{'type':'text','text':line}]
            content_nodes.append(para)
    return {'type':'doc','content':content_nodes}

@app.route('/api/upload', methods=['POST'])
@require_auth
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    f = request.files['file']
    filename = f.filename or ''
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ('.txt', '.md'):
        return jsonify({'error': 'Only .txt and .md files are supported'}), 400
    if len(f.read()) > 5 * 1024 * 1024:
        return jsonify({'error': 'File too large (max 5MB)'}), 400
    f.seek(0)
    text = f.read().decode('utf-8', errors='replace')
    title = os.path.splitext(filename)[0]
    content = json.dumps(text_to_tiptap(text, filename))
    doc_id = str(uuid.uuid4())
    db = get_db()
    db.execute('INSERT INTO documents (id,title,content,owner_id) VALUES (?,?,?,?)',
               (doc_id, title, content, g.user['id']))
    db.commit()
    doc = row(db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone())
    return jsonify(doc), 201

# ── Frontend (serve index.html for all non-API routes) ────────────────────────

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    dist = os.path.join(os.path.dirname(__file__), 'frontend_dist')
    if path and os.path.exists(os.path.join(dist, path)):
        return send_from_directory(dist, path)
    return send_from_directory(dist, 'index.html')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
