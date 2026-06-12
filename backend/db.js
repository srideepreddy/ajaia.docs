const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, 'data.db');

let db;

function getDb() {
  if (!db) {
    db = new Database(DB_PATH);
    db.pragma('journal_mode = WAL');
    db.pragma('foreign_keys = ON');
    init();
  }
  return db;
}

function init() {
  const d = getDb();

  d.exec(`
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
  `);

  // Seed users
  const insertUser = d.prepare(`
    INSERT OR IGNORE INTO users (id, email, name, token) VALUES (?, ?, ?, ?)
  `);
  insertUser.run('user-alice', 'alice@test.com', 'Alice Chen', 'token-alice-123');
  insertUser.run('user-bob', 'bob@test.com', 'Bob Martinez', 'token-bob-456');
  insertUser.run('user-carol', 'carol@test.com', 'Carol Singh', 'token-carol-789');

  // Seed a sample document for alice
  const existingDoc = d.prepare('SELECT id FROM documents WHERE id = ?').get('doc-sample-1');
  if (!existingDoc) {
    d.prepare(`
      INSERT INTO documents (id, title, content, owner_id) VALUES (?, ?, ?, ?)
    `).run(
      'doc-sample-1',
      'Welcome to AjaiaDocs',
      JSON.stringify({
        type: 'doc',
        content: [
          { type: 'heading', attrs: { level: 1 }, content: [{ type: 'text', text: 'Welcome to AjaiaDocs' }] },
          { type: 'paragraph', content: [{ type: 'text', text: 'This is a collaborative document editor. You can format text using the toolbar above.' }] },
          { type: 'heading', attrs: { level: 2 }, content: [{ type: 'text', text: 'Features' }] },
          { type: 'bulletList', content: [
            { type: 'listItem', content: [{ type: 'paragraph', content: [{ type: 'text', marks: [{ type: 'bold' }], text: 'Rich text editing' }, { type: 'text', text: ' — bold, italic, underline, headings' }] }] },
            { type: 'listItem', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Upload .txt and .md files to create documents' }] }] },
            { type: 'listItem', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Share documents with other users' }] }] },
            { type: 'listItem', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'All changes are automatically saved' }] }] }
          ]}
        ]
      }),
      'user-alice'
    );
  }
}

module.exports = { getDb };
