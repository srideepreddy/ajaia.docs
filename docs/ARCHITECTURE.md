# Architecture Note

## Stack

| Layer | Choice | Reason |
|---|---|---|
| Backend | Python / Flask | Available in deployment environment, minimal setup, built-in dev server |
| Database | SQLite (stdlib `sqlite3`) | Zero-install, file-based, survives restarts, sufficient for this scope |
| Frontend | Single-page HTML (React via CDN, contenteditable editor) | No build step required — the Flask server serves one HTML file. Reviewers can run with `python server.py` and nothing else. |
| Auth | Token-based (seeded demo tokens) | Demonstrates the sharing model cleanly without OAuth complexity |

## What I prioritized and why

**1. Editor first.** The assignment says "the editing experience should feel usable." I chose a `contenteditable` div with `document.execCommand` for formatting — this is the same mechanism underlying Google Docs circa 2010. It gives real bold/italic/underline/headings/lists/blockquotes without any npm dependency, which mattered given the deployment constraint.

**2. Sharing model next.** This is the hardest requirement to fake — it needs actual multi-user logic. I built it with three clean database concepts: `users`, `documents` (owner FK), and `document_shares` (doc_id × user_id join table). The sharing logic is enforced at the API layer: every document fetch checks ownership OR share membership before returning data.

**3. File upload scoped tightly.** Supporting .txt and .md covers the spirit of the requirement without pulling in a docx parser. The markdown-to-HTML conversion is a simple line-by-line pass that correctly handles `#`, `##`, `###` headings and wraps everything else in `<p>` tags.

**4. Single-file deployment.** The Flask server serves the frontend HTML at `/` and all API routes at `/api/*`. No separate frontend build, no CORS configuration, no reverse proxy needed. This keeps local setup to two commands: `pip install flask` and `python server.py`.

## Database schema

```sql
users (id, email, name, token)
documents (id, title, content, owner_id, created_at, updated_at)
document_shares (doc_id, shared_with_id, granted_at)
```

Content is stored as HTML (from `innerHTML` of the contenteditable div). This is simple and lossless — the same HTML is injected back on open, preserving all formatting exactly. An alternative would be storing Prosemirror/Tiptap JSON, but that requires the npm build chain.

## What I would change with more time

- **Real-time collaboration** — SSE (Server-Sent Events) for presence indicators; WebSockets for live co-editing with operational transforms or CRDTs
- **Tiptap editor** — replace `execCommand` (deprecated) with Tiptap/Prosemirror for better cross-browser consistency and structured JSON storage
- **Role-based sharing** — edit / view / comment permissions stored in `document_shares.permission` column
- **`.docx` import** — `python-docx` library to parse Word documents on upload
- **Export** — `weasyprint` for PDF export, raw HTML for Markdown export
- **Deployment** — Containerise with Docker, use PostgreSQL on Railway/Render for production persistence

## Security notes

- IDOR protection: every document API endpoint verifies ownership or share membership before returning data
- Bob cannot access Alice's private docs (covered by tests)
- Non-owners cannot share, delete, or edit documents they were shared into
- Token auth is demo-grade (hardcoded tokens) — production would use JWT or session cookies
