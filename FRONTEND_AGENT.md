# Frontend Agent — Vibe Search

You are the frontend developer. `PLAN.md` is your source of truth.

## Stack
- **Framework:** React 18 + Vite
- **Styling:** Tailwind CSS
- **Charts:** Plotly.js (for UMAP/t-SNE visualization later)
- **Realtime:** SSE via EventSource for progress streaming
- **Backend:** FastAPI at `http://localhost:8000`

## Your Tasks
Work through `## Frontend` tasks in `PLAN.md`. All backend contracts are ready:
1. **1.1** Scaffold Vite + React + Tailwind
2. **1.2** Spotify OAuth connect + sync UI
3. **1.3** Download progress UI
4. **1.4** Embed progress UI
5. **1.5** Search UI
6. **1.6** Pipeline status dashboard

## API Contracts

### Auth & Sync
- `GET /api/auth/url` → `{ url: string }` — Spotify OAuth URL
- `GET /api/auth/callback?code=` → `{ status: "authenticated" }`
- `GET /api/auth/status` → `{ authenticated: boolean }`
- `POST /api/sync { playlist_id }` → `{ status: "started" }`
- `GET /api/sync/stream` → SSE: progress/complete/error

### Download
- `POST /api/download` → `{ status: "started", total: number }`
- `GET /api/download/stream` → SSE: `{ current, total, success, failed, active, song }`

### Embed
- `POST /api/embed` → `{ status: "started", total: number }`
- `GET /api/embed/stream` → SSE: `{ current, total, song }`

### Search & Library
- `POST /api/search { query, n_results }` → `{ results: [{ spotify_id, title, artist, album, album_art_url, spotify_link, similarity_score }] }`
- `GET /api/library` → `{ songs: [...], stats: { total, downloaded, embedded } }`

## SSE Pattern
```javascript
const es = new EventSource('http://localhost:8000/api/sync/stream');
es.addEventListener('progress', (e) => { const data = JSON.parse(e.data); });
es.addEventListener('complete', (e) => { es.close(); });
es.addEventListener('error', (e) => { es.close(); });
```

## Rules
- Do NOT touch `backend/` files
- Do NOT invent endpoints — if unclear, note it in `PLAN.md`
- If you see `⚠️ CONTRACT CHANGED`, update your implementation

## Visual Verification
Screenshot your work. Check: layout, responsiveness, interactive states. Fix before marking done.
