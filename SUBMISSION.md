# SUBMISSION.md

## What's included

| File / Folder | Description |
|---|---|
| `backend/server.py` | Flask REST API — auth, documents, sharing, file upload |
| `backend/db.py` | SQLite setup, schema creation, seed data |  
| `backend/auth.py` | Auth middleware (`require_auth` decorator) |
| `backend/test_server.py` | 17 automated tests (stdlib unittest) |
| `backend/frontend_dist/index.html` | Full single-page frontend (React via CDN, no build step) |
| `README.md` | Local setup, deployment, feature list, scope decisions |
| `docs/ARCHITECTURE.md` | Stack choices, schema, prioritization rationale |
| `docs/AI_WORKFLOW.md` | AI tools used, what was changed/rejected, verification approach |
| `SUBMISSION.md` | This file |

## Feature status

| Requirement | Status | Notes |
|---|---|---|
| Document creation | ✅ Working | + New button, auto-named "Untitled" |
| Rename document | ✅ Working | Edit title in-place at top of editor |
| Rich text editing | ✅ Working | Bold, italic, underline, H1/H2/H3, bullet list, numbered list, blockquote |
| Save + reopen | ✅ Working | Auto-save with 1.2s debounce; Ctrl+S for immediate save |
| File upload (.txt, .md) | ✅ Working | Creates new editable doc; markdown headings parsed |
| Sharing model | ✅ Working | Owner shares by email; non-owners see doc as read-only |
| Owned vs shared distinction | ✅ Working | Sidebar badges; "Mine" vs "Shared" |
| Persistence | ✅ Working | SQLite; survives server restart |
| Automated test | ✅ Working | 17 tests across auth, documents, sharing, upload |
| Deployment | ✅ Ready | `python server.py` — one command local; Railway/Render for cloud |
| Real-time collaboration | ❌ Intentionally cut | Would need WebSockets + CRDT/OT |
| .docx upload | ❌ Intentionally cut | Stated in UI: only .txt and .md supported |
| Version history | ❌ Intentionally cut | Stretch goal |

## Credentials for testing sharing flow

1. Log in as `alice@test.com` — she has a sample "Welcome to AjaiaDocs" document
2. Open the doc, click **Share**, enter `bob@test.com`
3. Sign out, log in as `bob@test.com` — the doc appears in "Shared with me"
4. Bob can read but not edit (read-only toolbar is shown)
5. Log back in as alice, open the doc, Share → Remove bob to revoke

## Run tests

```bash
cd backend
python test_server.py -v
# Expected: Ran 17 tests in ~0.2s — OK
```

## What I'd build next (2–4 more hours)

1. Real-time presence indicators (Server-Sent Events) — show who else has the doc open
2. Role-based sharing (edit / view / comment) — `permission` column in `document_shares`
3. `.docx` import via `python-docx`
4. Export to PDF (`weasyprint`) or Markdown
5. Replace `execCommand` with Tiptap/Prosemirror for better cross-browser formatting reliability
