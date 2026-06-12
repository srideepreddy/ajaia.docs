# AjaiaDocs — Collaborative Document Editor

A lightweight Google Docs-inspired editor with rich text editing, file import, document sharing, and full persistence.

## Live Demo

> Deploy instructions below. Once running, open `http://localhost:5000`.

**Demo accounts (no password required):**
| Email | Name |
|---|---|
| alice@test.com | Alice Chen |
| bob@test.com | Bob Martinez |
| carol@test.com | Carol Singh |

---

## Local Setup

### Requirements
- Python 3.9+
- pip

### Install and run

```bash
# 1. Clone / unzip the project
cd backend

# 2. Install Python dependencies
pip install flask

# 3. Start the server (initialises DB + seeds demo data automatically)
python server.py

# 4. Open http://localhost:5000
```

The SQLite database (`data.db`) is created automatically on first run. No separate database setup needed.

### Run tests

```bash
cd backend
python test_server.py -v
```

Expected output: 17 tests, all OK.

---

## Deployment (Railway)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

Set `PORT` environment variable if needed (defaults to 5000).

Alternatively, deploy to **Render** (free tier):
1. Connect your GitHub repo
2. Set build command: `pip install flask`
3. Set start command: `python backend/server.py`
4. Set `PORT=10000` in environment variables

---

## Features

### Document editing
- Create, rename, delete documents
- Rich text formatting: bold, italic, underline, headings (H1/H2/H3), bullet lists, numbered lists, blockquotes
- Auto-save with 1.2s debounce after any keystroke
- Ctrl/Cmd+S for immediate save

### File upload
- Supported formats: `.txt` and `.md` (max 5MB)
- Markdown headings (`#`, `##`, `###`) are parsed and rendered as proper heading nodes
- Uploaded file becomes a new editable document in your library

### Sharing
- Share any document you own by entering another user's email
- Shared users can read the document (view-only for non-owners by design — the owner retains edit control)
- Sidebar shows "Mine" badge for owned docs and "Shared" badge for shared docs
- Owner can revoke access at any time via the Share modal

### Persistence
- SQLite database — survives server restarts
- Document content stored as HTML (from contenteditable)
- Sharing relationships stored in a `document_shares` join table

---

## What's not included (intentional scope cuts)

| Feature | Decision |
|---|---|
| Real-time collaboration (websockets) | Deprioritized — core editing + sharing covers the brief |
| `.docx` upload | python-docx parsing adds significant complexity; .txt/.md stated clearly in UI |
| Role-based permissions (edit vs view) | All non-owners are read-only; stated as a deliberate simplification |
| Document version history | Optional stretch goal; skipped to finish core features |
| OAuth / real auth | Seeded token-based auth demonstrates the sharing logic cleanly |

With another 2–4 hours I would add: real-time presence indicators via Server-Sent Events, `.docx` import using `python-docx`, and role-based sharing (edit / view / comment).
