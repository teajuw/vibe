# Vibe Search

## Overview
Semantic music search: describe a vibe in natural language → get matching songs from your Spotify library via CLAP audio embeddings.

## Stack
- **Backend:** FastAPI, SQLite + SQLModel, ChromaDB, laion-clap, yt-dlp, spotipy
- **Frontend:** React (Vite), Tailwind, Plotly
- **Coordination:** SSE for progress streaming

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        SQLite (songs.db)                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ songs table                                            │ │
│  │ - spotify_id (PK)    - download_status                 │ │
│  │ - title, artist      - embed_status                    │ │
│  │ - album, uri         - file_path                       │ │
│  │ - album_art_url      - created_at, updated_at          │ │
│  │ - spotify_link                                         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ spotify_id links both
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     ChromaDB (data/chroma/)                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ songs collection                                       │ │
│  │ - id = spotify_id                                      │ │
│  │ - embedding[512]     (CLAP audio vector)               │ │
│  │ - metadata: title, artist, album (for search display)  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**SQLite handles:** CRUD, status tracking, queries ("show failed downloads")
**ChromaDB handles:** Vector similarity search ("find songs like this vibe")

---

## Phase 1: MVP

### Backend

#### [x] 1.1 Project scaffolding + SQLite
- FastAPI app with CORS ✓
- SQLite + SQLModel database ✓
- ChromaDB persistent client ✓
- Config, router stubs ✓

Files: `backend/main.py`, `backend/config.py`, `backend/database.py`, `backend/models.py`

#### [x] 1.2 Spotify playlist sync
- OAuth flow via spotipy
- Fetch tracks from playlist
- Upsert to SQLite (skip existing songs)
- SSE progress stream

```
GET /api/auth/url → { url: string }
GET /api/auth/callback?code=... → { status: "authenticated" }
GET /api/auth/status → { authenticated: boolean }
POST /api/sync { playlist_id } → { status: "started" }
GET /api/sync/stream → SSE: progress/complete/error events
```

#### [x] 1.3 Audio download (yt-dlp)
- Query SQLite: `WHERE download_status = 'pending'`
- yt-dlp with 4 concurrent downloads
- Update status in DB on completion/failure
- SSE progress

```
POST /api/download → { status: "started" }
GET /api/download/stream → SSE progress events
```

#### [x] 1.4 CLAP embedding
- Query SQLite: `WHERE download_status = 'done' AND embed_status = 'pending'`
- Generate 512-dim embedding
- Insert to ChromaDB
- Update SQLite embed_status
- SSE progress

```
POST /api/embed → { status: "started" }
GET /api/embed/stream → SSE progress events
```

#### [x] 1.5 Search endpoint
- CLAP text encoding → ChromaDB query
- Return results with metadata

```
POST /api/search { query, n_results } → { results: [...] }
```

#### [x] 1.6 Library state endpoint
- Query SQLite for all songs + stats

```
GET /api/library → { songs: [...], stats: { total, downloaded, embedded } }
```

---

### Frontend

#### [ ] 1.1 Project scaffolding
- Vite + React + Tailwind
- API client, SSE hook

#### [ ] 1.2 Spotify connect + sync UI
- "Connect Spotify" button → OAuth redirect
- Playlist ID input
- Sync button → shows SSE progress

Depends on: Backend 1.2 ✓

#### [ ] 1.3 Download progress UI
- "Start Download" button
- Per-song status table
- Overall progress bar

Depends on: Backend 1.3 ✓

#### [ ] 1.4 Embed progress UI
- "Generate Embeddings" button
- Progress bar with song count

Depends on: Backend 1.4 ✓

#### [ ] 1.5 Search UI
- Query input field
- Results list with album art, title, artist, similarity score
- Spotify link to open songs

Depends on: Backend 1.5 ✓

#### [ ] 1.6 Pipeline status dashboard

---

## Notes

### File Structure
```
vibe-search/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py        # SQLite + SQLModel
│   ├── models.py
│   └── routers/
│       ├── sync.py
│       ├── download.py
│       ├── embed.py
│       └── search.py
├── frontend/
├── data/
│   ├── songs.db           # SQLite database
│   └── chroma/
├── audio/
├── .env
└── requirements.txt
```

### Verification
1. Run backend: `uvicorn backend.main:app --reload`
2. Run frontend: `cd frontend && npm run dev`
3. Connect Spotify, sync playlist
4. Verify songs in DB: `python -c "from backend.database import get_session; ..."`
5. Download, embed, search
