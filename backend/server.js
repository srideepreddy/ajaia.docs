const express = require('express');
const cors = require('cors');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const { getDb } = require('./db');
const { requireAuth } = require('./auth');

const app = express();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 5 * 1024 * 1024 }, // 5MB
  fileFilter: (req, file, cb) => {
    const allowed = ['.txt', '.md'];
    const ext = path.extname(file.originalname).toLowerCase();
    if (allowed.includes(ext)) cb(null, true);
    else cb(new Error('Only .txt and .md files are supported'));
  }
});

app.use(cors());
app.use(express.json({ limit: '10mb' }));

// ── Auth ──────────────────────────────────────────────────────────────────────
app.post('/api/auth/login', (req, res) => {
  const { email } = req.body;
  if (!email) return res.status(400).json({ error: 'Email required' });

  const user = getDb().prepare('SELECT id, email, name, token FROM users WHERE email = ?').get(email);
  if (!user) return res.status(404).json({ error: 'No user with that email. Try alice@test.com, bob@test.com, or carol@test.com' });

  res.json({ user: { id: user.id, email: user.email, name: user.name }, token: user.token });
});

app.get('/api/auth/me', requireAuth, (req, res) => {
  res.json({ id: req.user.id, email: req.user.email, name: req.user.name });
});

// ── Users ─────────────────────────────────────────────────────────────────────
app.get('/api/users', requireAuth, (req, res) => {
  const users = getDb()
    .prepare('SELECT id, email, name FROM users WHERE id != ?')
    .all(req.user.id);
  res.json(users);
});

// ── Documents ─────────────────────────────────────────────────────────────────
app.get('/api/documents', requireAuth, (req, res) => {
  const db = getDb();
  const owned = db.prepare(`
    SELECT id, title, owner_id, created_at, updated_at, 'owned' as relation
    FROM documents WHERE owner_id = ?
    ORDER BY updated_at DESC
  `).all(req.user.id);

  const shared = db.prepare(`
    SELECT d.id, d.title, d.owner_id, d.created_at, d.updated_at,
           'shared' as relation, u.name as owner_name, u.email as owner_email
    FROM documents d
    JOIN document_shares ds ON ds.doc_id = d.id
    JOIN users u ON u.id = d.owner_id
    WHERE ds.shared_with_id = ?
    ORDER BY d.updated_at DESC
  `).all(req.user.id);

  res.json({ owned, shared });
});

app.post('/api/documents', requireAuth, (req, res) => {
  const { title = 'Untitled', content = '' } = req.body;
  const id = uuidv4();
  getDb().prepare(`
    INSERT INTO documents (id, title, content, owner_id) VALUES (?, ?, ?, ?)
  `).run(id, title, typeof content === 'string' ? content : JSON.stringify(content), req.user.id);

  const doc = getDb().prepare('SELECT * FROM documents WHERE id = ?').get(id);
  res.status(201).json(doc);
});

app.get('/api/documents/:id', requireAuth, (req, res) => {
  const db = getDb();
  const doc = db.prepare('SELECT * FROM documents WHERE id = ?').get(req.params.id);
  if (!doc) return res.status(404).json({ error: 'Document not found' });

  const isOwner = doc.owner_id === req.user.id;
  const isShared = db.prepare(
    'SELECT 1 FROM document_shares WHERE doc_id = ? AND shared_with_id = ?'
  ).get(req.params.id, req.user.id);

  if (!isOwner && !isShared) return res.status(403).json({ error: 'Access denied' });

  const owner = db.prepare('SELECT id, name, email FROM users WHERE id = ?').get(doc.owner_id);
  const shares = db.prepare(`
    SELECT u.id, u.name, u.email FROM document_shares ds
    JOIN users u ON u.id = ds.shared_with_id
    WHERE ds.doc_id = ?
  `).all(doc.id);

  res.json({ ...doc, owner, shares, relation: isOwner ? 'owned' : 'shared' });
});

app.put('/api/documents/:id', requireAuth, (req, res) => {
  const db = getDb();
  const doc = db.prepare('SELECT * FROM documents WHERE id = ?').get(req.params.id);
  if (!doc) return res.status(404).json({ error: 'Document not found' });
  if (doc.owner_id !== req.user.id) return res.status(403).json({ error: 'Only the owner can edit this document' });

  const { title, content } = req.body;
  const newTitle = title !== undefined ? title : doc.title;
  const newContent = content !== undefined
    ? (typeof content === 'string' ? content : JSON.stringify(content))
    : doc.content;

  db.prepare(`
    UPDATE documents SET title = ?, content = ?, updated_at = datetime('now') WHERE id = ?
  `).run(newTitle, newContent, req.params.id);

  res.json(db.prepare('SELECT * FROM documents WHERE id = ?').get(req.params.id));
});

app.delete('/api/documents/:id', requireAuth, (req, res) => {
  const doc = getDb().prepare('SELECT * FROM documents WHERE id = ?').get(req.params.id);
  if (!doc) return res.status(404).json({ error: 'Not found' });
  if (doc.owner_id !== req.user.id) return res.status(403).json({ error: 'Only the owner can delete this document' });
  getDb().prepare('DELETE FROM documents WHERE id = ?').run(req.params.id);
  res.json({ success: true });
});

// ── Sharing ───────────────────────────────────────────────────────────────────
app.post('/api/documents/:id/share', requireAuth, (req, res) => {
  const db = getDb();
  const doc = db.prepare('SELECT * FROM documents WHERE id = ?').get(req.params.id);
  if (!doc) return res.status(404).json({ error: 'Document not found' });
  if (doc.owner_id !== req.user.id) return res.status(403).json({ error: 'Only the owner can share' });

  const { email } = req.body;
  if (!email) return res.status(400).json({ error: 'Email required' });

  const target = db.prepare('SELECT * FROM users WHERE email = ?').get(email);
  if (!target) return res.status(404).json({ error: `No user found with email: ${email}` });
  if (target.id === req.user.id) return res.status(400).json({ error: 'Cannot share with yourself' });

  db.prepare(`
    INSERT OR IGNORE INTO document_shares (doc_id, shared_with_id) VALUES (?, ?)
  `).run(req.params.id, target.id);

  res.json({ success: true, sharedWith: { id: target.id, name: target.name, email: target.email } });
});

app.delete('/api/documents/:id/share/:userId', requireAuth, (req, res) => {
  const db = getDb();
  const doc = db.prepare('SELECT * FROM documents WHERE id = ?').get(req.params.id);
  if (!doc) return res.status(404).json({ error: 'Not found' });
  if (doc.owner_id !== req.user.id) return res.status(403).json({ error: 'Only the owner can revoke access' });

  db.prepare('DELETE FROM document_shares WHERE doc_id = ? AND shared_with_id = ?')
    .run(req.params.id, req.params.userId);
  res.json({ success: true });
});

// ── File Upload ───────────────────────────────────────────────────────────────
app.post('/api/upload', requireAuth, upload.single('file'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file provided' });

  const text = req.file.buffer.toString('utf-8');
  const title = path.basename(req.file.originalname, path.extname(req.file.originalname));

  // Convert plain text to Tiptap JSON
  const lines = text.split('\n');
  const content = {
    type: 'doc',
    content: lines.map(line => {
      if (line.startsWith('# ')) {
        return { type: 'heading', attrs: { level: 1 }, content: [{ type: 'text', text: line.slice(2) }] };
      } else if (line.startsWith('## ')) {
        return { type: 'heading', attrs: { level: 2 }, content: [{ type: 'text', text: line.slice(3) }] };
      } else if (line.startsWith('### ')) {
        return { type: 'heading', attrs: { level: 3 }, content: [{ type: 'text', text: line.slice(4) }] };
      } else {
        return {
          type: 'paragraph',
          content: line.trim() ? [{ type: 'text', text: line }] : []
        };
      }
    })
  };

  const id = uuidv4();
  getDb().prepare(`
    INSERT INTO documents (id, title, content, owner_id) VALUES (?, ?, ?, ?)
  `).run(id, title, JSON.stringify(content), req.user.id);

  const doc = getDb().prepare('SELECT * FROM documents WHERE id = ?').get(id);
  res.status(201).json(doc);
});

// ── Error handler ─────────────────────────────────────────────────────────────
app.use((err, req, res, next) => {
  if (err.message?.includes('Only .txt')) {
    return res.status(400).json({ error: err.message });
  }
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
});

const PORT = process.env.PORT || 3001;
if (require.main === module) {
  getDb(); // init DB
  app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
}

module.exports = app;
