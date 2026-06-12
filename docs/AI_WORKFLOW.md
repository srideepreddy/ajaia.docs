# AI Workflow Note

## Tools used

- **Claude (Anthropic)** — primary assistant throughout the build

## Where AI materially sped up the work

1. **Scaffolding the Flask API** — Claude generated the full route structure (auth, documents, sharing, upload) in one pass. This would have taken 45–60 minutes by hand; it took ~5 minutes to review and adjust.

2. **SQLite schema + seed logic** — The three-table schema and seed data were generated correctly on the first attempt. Minor tweak: added `PRAGMA foreign_keys=ON` after seeing a cascade delete wasn't working in testing.

3. **Frontend HTML/CSS** — The sidebar + editor layout with CSS variables and responsive design was generated quickly. I rewrote the Toolbar component after the first version used `onclick` attributes in HTML strings rather than React event handlers.

4. **Test suite** — The 17 tests covering all four feature areas (auth, documents, sharing, upload) were generated as a complete file. I changed the test runner from `pytest` to stdlib `unittest` when the environment didn't have pip access, and rewrote the `setUp` method to use `init_db()` correctly with Flask's app context.

5. **Markdown-to-HTML conversion in `text_to_tiptap`** — One-pass solution worked correctly on first generation.

## What AI-generated output I changed or rejected

**Changed:**
- Toolbar: AI first generated formatting buttons using HTML `onclick` strings. Replaced with React `onMouseDown` + `e.preventDefault()` pattern to prevent focus loss on the editor.
- Test runner: switched from `pytest` to `unittest` for environment compatibility. All test logic was preserved.
- `init_db` function: AI initially put DB initialisation inside `get_db()` using `g`, which doesn't work for test setup outside a request context. Split into a standalone `init_db()` callable.

**Rejected:**
- AI suggested using `localStorage` for document content caching as a "performance optimization." Rejected — this adds hidden state that would cause confusing stale-content bugs during the sharing demo.
- AI proposed a React-based frontend with a Vite build pipeline. Rejected in favour of a single HTML file to keep the setup to one command (`python server.py`).
- AI suggested `flask-cors` for cross-origin requests. Rejected — unnecessary since the Flask server serves the frontend directly at the same origin.

## How I verified correctness

- Ran the 17-test suite after every significant change
- Manually tested the full user flow: login → create doc → format text → upload .md file → share with bob → log in as bob → verify read-only access → revoke share → verify 403
- Checked that SQLite foreign key cascades worked (deleting a doc removes its shares)
- Verified save debounce timing didn't lose content by typing quickly and watching the save status indicator

## Assessment

AI cut approximately 2–3 hours off a 6-hour task. The value was highest in boilerplate generation (routes, CSS, tests) and lowest where product judgment was needed (what to scope out, how to structure the sharing UX, which tech choices kept setup simple for reviewers).
