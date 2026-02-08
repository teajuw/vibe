# Vibe Search — Project Plan & Implementation Guide

## What This Is

A personal music search engine that lets you describe a mood, vibe, or theme in natural language and returns a playlist from your own Spotify library. The core idea: CLAP (Contrastive Language-Audio Pretraining) embeds both audio files and text descriptions into the same 512-dimensional vector space. When a user types "melancholic late night drive," the text gets embedded into that same space, and nearest-neighbor search finds the songs whose audio embeddings are closest to that text vector.

## Why This Exists

Spotify removed audio-features, audio-analysis, and recommendations endpoints in Nov 2024. Their native playlist tools don't support semantic/vibe-based organization. This app replaces all of that with something more powerful — direct audio understanding via CLAP, stored in a vector DB for instant semantic search.

---

## Architecture Overview

```
User's Spotify Account
        │
        ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  1. LIBRARY SYNC │────▶│  2. DOWNLOAD     │────▶│  3. LYRICS       │
│  (spotipy)       │     │  (yt-dlp)        │     │  (Genius API)    │
│  GET /me/tracks  │     │  → audio/*.mp3   │     │  → lyrics text   │
│  + album art URLs│     │  audio-only, 4   │     │  stored as       │
│  + track URIs    │     │  concurrent      │     │  metadata        │
└──────────────────┘     └────────┬─────────┘     └────────┬─────────┘
                                  │                         │
                                  ▼                         │
                         ┌──────────────────┐               │
                         │  4. EMBED        │               │
                         │  (CLAP audio     │               │
                         │   encoder, CUDA) │               │
                         └────────┬─────────┘               │
                                  │                         │
                                  ▼                         ▼
                         ┌──────────────────────────────────────┐
                         │  5. STORE (ChromaDB)                 │
                         │  512-dim vectors + metadata          │
                         │  (title, artist, album, lyrics,     │
                         │   album_art_url, spotify_uri,       │
                         │   spotify_link, added_at)           │
                         └────────┬─────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼              ▼
             ┌───────────┐ ┌──────────┐  ┌────────────┐
             │ 6. SEARCH │ │7. CLUSTER│  │8. VISUALIZE│
             │ text query│ │ HDBSCAN  │  │ UMAP/t-SNE │
             │ → top N   │ │ on 512-d │  │ → 2D plot  │
             └─────┬─────┘ └────┬─────┘  └────────────┘
                   │             │
                   ▼             ▼
             ┌──────────────────────────┐
             │ 9. EXPORT → Spotify      │
             │ • Playlist from search   │
             │ • Playlist from cluster  │
             │ • Playlist from KNN      │
             │ • Playlist from lasso    │
             └──────────────────────────┘
```

---

## Tech Stack

| Component        | Tool                                          | Why                                                              |
|------------------|-----------------------------------------------|------------------------------------------------------------------|
| Backend          | FastAPI                                       | Native SSE support, async, Python ecosystem for ML libs          |
| Frontend         | React (Vite) + Tailwind                       | Fast dev, good for dashboards                                    |
| Progress Updates | Server-Sent Events (SSE)                      | Simpler than WebSockets for one-way server→client progress       |
| Spotify API      | spotipy (PKCE auth flow)                      | Mature Python Spotify wrapper, handles pagination                |
| Audio Download   | yt-dlp (direct, audio-only)                   | Simpler than spotdl, no internal throttling, fewer deps          |
| Lyrics           | lyricsgenius (Genius API)                     | 1.7M+ searchable songs, human-verified, fast (~1-2 sec/song)    |
| Embeddings       | laion-clap                                    | Joint audio-text embedding space, pip installable, pretrained    |
| CLAP Checkpoint  | `music_speech_audioset_epoch_15_esc_89.98.pt` | Music-optimized checkpoint (vs general audio)                    |
| Vector Store     | ChromaDB (persistent, local)                  | Zero config, pip install, runs in-process, cosine similarity     |
| Clustering       | HDBSCAN                                       | No need to specify K, discovers clusters + outliers              |
| Visualization    | UMAP + t-SNE (sklearn / umap-learn)           | Dimensionality reduction for 2D scatter plots                    |
| Plot Rendering   | Plotly (frontend)                             | Interactive scatter with hover, click, lasso select              |
| GPU              | CUDA available                                | User has CUDA GPU for CLAP inference                             |

---

## Per-Song Timing Budget

| Step                     | Time per song | Parallelizable? | Bottleneck          |
|--------------------------|---------------|-----------------|---------------------|
| Spotify metadata fetch   | ~0.01 sec     | Batched (50/req)| API rate limit      |
| yt-dlp search + download | ~15-30 sec    | Yes (4 concurrent)| Network + YT search|
| Genius lyrics lookup     | ~1-2 sec      | Yes (5 concurrent)| API rate limit     |
| CLAP inference (CUDA)    | ~0.5-1 sec    | Sequential (GPU)| GPU compute         |
| ChromaDB insert          | ~instant      | N/A             | None                |
| **Total per song**       | **~20-35 sec**| —               | **Download dominates** |

**At 4 concurrent downloads:**
- 100 songs: ~10-15 minutes
- 500 songs: ~45-90 minutes
- 1000 songs: ~2-3 hours

---

## Spotify API — What Still Works (as of Feb 2026)

These endpoints are confirmed available:

**Library & Metadata (MVP)**
| Endpoint                        | Purpose                    |
|---------------------------------|----------------------------|
| `GET /me/tracks`                | Fetch liked songs (paginated, 50/request) |
| `GET /me/tracks/contains`       | Check if tracks are in liked songs |
| `GET /me/playlists`             | List user's playlists      |
| `GET /playlists/{id}/tracks`    | Get tracks from a specific playlist |
| `POST /playlists/{id}/tracks`   | Add tracks to playlist     |
| `DELETE /playlists/{id}/tracks` | Remove tracks from playlist |
| `PUT /playlists/{id}`           | Update playlist details    |
| `GET /me`                       | Current user profile       |
| `GET /search`                   | Search catalog             |

**Playback Control (Post-MVP, requires Premium)**
| Endpoint                        | Purpose                    |
|---------------------------------|----------------------------|
| `PUT /me/player/play`           | Start/resume playback      |
| `PUT /me/player/pause`          | Pause playback             |
| `POST /me/player/queue`         | Add item to queue          |
| `GET /me/player/devices`        | Available devices          |
| `GET /me/player/currently-playing` | Current track           |
| `PUT /me/player`                | Transfer playback          |
| `PUT /me/player/seek`           | Seek to position           |
| `PUT /me/player/shuffle`        | Toggle shuffle             |
| `PUT /me/player/volume`         | Set volume                 |
| `GET /me/player/recently-played`| Recent history             |

**What's gone (and we don't need):** `audio-features`, `audio-analysis`, `recommendations`, `get-several-artists`, `get-several-albums`, `artist-top-tracks`, `create-playlist-for-user` (use `POST /me/playlists` instead).

**Auth:** PKCE flow (no client secret needed). Scopes needed:
- MVP: `user-library-read`, `playlist-modify-public`, `playlist-modify-private`
- Post-MVP: add `user-read-playback-state`, `user-modify-playback-state`, `streaming`

---

## Critical Design Decisions

### Why yt-dlp and not spotdl?
spotdl wraps yt-dlp internally but adds its own throttling layer and Spotify metadata matching logic. Going directly to yt-dlp with `ytsearch:"artist - title"` is simpler, has fewer dependencies, and gives us direct control over concurrency. Tradeoff: spotdl does smarter matching using Spotify metadata; raw YouTube search might occasionally grab wrong versions (live, remix, cover). For MVP, yt-dlp is the right call.

### Album art — no download needed
Spotify's API returns album art URLs (`album.images[]`) in the track metadata. We get 640x640 art URLs for free during library sync. Store the URL, render from Spotify's CDN. Zero cost.

### Why CLAP and not Librosa?
CLAP is a pretrained neural model that maps audio and text into the same embedding space. It understands "vibe" at a level hand-crafted features (MFCCs, spectral centroids) cannot. We don't need Librosa at all.

### Why cluster on 512-dim, not on 2D projections?
UMAP and t-SNE are lossy transformations optimized for visual layout. Clustering on 2D projections produces artifacts. The correct workflow: cluster in 512-dim → project to 2D → color by cluster label.

### Why HDBSCAN and not K-means?
K-means requires specifying K upfront. HDBSCAN discovers clusters automatically and identifies outlier/noise points. Better for exploratory use.

### Will 512 dimensions cause curse-of-dimensionality problems?
No. CLAP's 512 dims are a learned compressed representation — dense and meaningful. With hundreds to low thousands of songs, cosine similarity remains discriminative.

### Why ChromaDB?
Zero configuration. `pip install chromadb`, create a collection, insert vectors. Persists to disk. Cosine similarity native. Sufficient for <10K songs.

### Why SSE and not WebSockets?
Progress updates are one-directional (server → client). SSE is simpler, auto-reconnects, and works through proxies.

---

## Implementation Phases

---

### Phase 1: MVP — Core Pipeline + Search + Links

**Goal:** Connect Spotify, download audio, fetch lyrics, embed with CLAP, search by vibe, get results with Spotify links to instantly open songs.

#### Task 1.1: Project Scaffolding
- Initialize FastAPI backend with CORS middleware
- Initialize React + Vite frontend with Tailwind
- Set up `.env` for `SPOTIFY_CLIENT_ID`, `SPOTIFY_REDIRECT_URI`, `GENIUS_ACCESS_TOKEN`
- Create shared Pydantic models for song state
- Set up ChromaDB persistent client in `db.py`

#### Task 1.2: Spotify Library Sync
- `POST /api/sync` — triggers library fetch
- `GET /api/sync/stream` — SSE endpoint for progress
- Use spotipy with PKCE auth flow
- Paginate through `current_user_saved_tracks()` (50 per page)
- Extract and store:
  ```python
  {
      spotify_id, title, artist, album, uri,
      added_at,
      album_art_url,    # from track['album']['images'][0]['url'] (640x640)
      spotify_link,     # f"https://open.spotify.com/track/{spotify_id}"
  }
  ```
- Save to `data/library.json`
- Frontend: "Connect Spotify" button → OAuth redirect → progress counter → song table with album art thumbnails

Song state model (used throughout the pipeline):
```python
class SongState(BaseModel):
    spotify_id: str
    title: str
    artist: str
    album: str
    uri: str              # spotify:track:xxx — needed for playlist writeback
    added_at: str
    album_art_url: str    # Spotify CDN URL for album cover
    spotify_link: str     # https://open.spotify.com/track/{id}
    download_status: str = "pending"  # pending | downloading | done | failed
    embed_status: str = "pending"     # pending | processing | stored | failed
    lyrics_status: str = "pending"    # pending | fetching | done | not_found | failed
    lyrics: Optional[str] = None
    file_path: Optional[str] = None
    cluster_id: Optional[int] = None
    cluster_name: Optional[str] = None
```

#### Task 1.3: Audio Download (yt-dlp)
- `POST /api/download` — triggers batch download
- `GET /api/download/stream` — SSE endpoint for per-song progress
- For each song with `download_status != "done"`:
  - Use yt-dlp Python API or subprocess:
    ```bash
    yt-dlp -x --audio-format mp3 --audio-quality 5 \
           -o "audio/%(id)s.%(ext)s" \
           "ytsearch1:{artist} - {title}"
    ```
  - Rename output to `audio/{spotify_id}.mp3`
  - Run up to 4 concurrent downloads (asyncio semaphore)
  - Update song state on completion/failure
- On failure: retry once, then mark as `failed` and continue
- Frontend: table with per-song status, overall progress bar, count

**Note:** yt-dlp searches YouTube for the track. Occasional mismatches are possible. For MVP, we accept this. The `ytsearch1:` prefix limits to the top result.

#### Task 1.4: Genius Lyrics Fetch
- `POST /api/lyrics` — triggers batch lyrics fetch
- `GET /api/lyrics/stream` — SSE endpoint for progress
- Use `lyricsgenius` Python library:
  ```python
  import lyricsgenius
  genius = lyricsgenius.Genius(access_token, timeout=10, retries=3)
  song = genius.search_song(title, artist)
  lyrics = song.lyrics if song else None
  ```
- Run up to 5 concurrent lookups
- Store lyrics text in song state AND as ChromaDB metadata
- Mark as `not_found` if Genius has no match (don't retry these)
- Frontend: lyrics status column, expandable to view lyrics text

**Rate limits:** Genius API is generous (~5 req/sec sustained). With 5 concurrent, 500 songs takes ~3-5 minutes.

#### Task 1.5: CLAP Embedding
- `POST /api/embed` — triggers batch embedding
- `GET /api/embed/stream` — SSE endpoint for progress
- Load CLAP model ONCE at startup (keep in memory via lifespan context):
  ```python
  import laion_clap
  model = laion_clap.CLAP_Module(enable_fusion=False, amodel='HTSAT-base')
  model.load_ckpt(ckpt='music_speech_audioset_epoch_15_esc_89.98.pt')
  ```
- For each song with `download_status == "done"` and `embed_status != "stored"`:
  - Load MP3, get audio embedding: `model.get_audio_embedding_from_filelist([file_path])`
  - Returns numpy array of shape `(1, 512)`
  - Insert into ChromaDB:
    ```python
    collection.add(
        ids=[spotify_id],
        embeddings=[embedding.tolist()],
        metadatas=[{
            "title": title, "artist": artist, "album": album,
            "uri": uri, "album_art_url": album_art_url,
            "spotify_link": spotify_link, "added_at": added_at,
            "lyrics": lyrics or ""
        }]
    )
    ```
- Skip songs already in ChromaDB (idempotent)
- Frontend: progress bar, songs processed count, ETA

**CLAP inference:** With CUDA, ~0.5-1 sec/song. 500 songs = ~5-10 minutes.

#### Task 1.6: Search
- `POST /api/search` — accepts `{query: string, n_results: int, expand: bool}`
- If `expand=true`, call LLM to expand query before CLAP encoding:
  ```python
  # Query expansion prompt (constrains LLM to CLAP-friendly vocabulary)
  EXPANSION_PROMPT = """You are translating a user's music search query into an audio
  description that a music-audio AI model will use to find matching songs.

  Output ONLY concrete acoustic descriptors from these categories:
  - Tempo: slow, moderate, fast, BPM range
  - Instruments: guitar, piano, synth, drums, bass, strings, horns, etc.
  - Vocals: male, female, soft, powerful, raspy, falsetto, choir, no vocals
  - Genre markers: rock, jazz, electronic, folk, hip-hop, classical, etc.
  - Production: lo-fi, polished, reverb-heavy, distorted, clean, ambient
  - Energy: calm, building, intense, explosive, subdued
  - Mood (audio-level): dark, bright, warm, cold, dreamy, aggressive

  Do NOT use abstract metaphors. Do NOT reference scenarios or activities.
  Convert the user's intent into what the music SOUNDS like.

  User query: "{query}"
  Audio description:"""
  ```
- Encode query text (raw or expanded) with CLAP:
  ```python
  text_embedding = model.get_text_embedding([query_text])  # shape (1, 512)
  ```
- Query ChromaDB:
  ```python
  results = collection.query(
      query_embeddings=[text_embedding.tolist()],
      n_results=n_results
  )
  ```
- Returns list of `{title, artist, album, spotify_id, spotify_link, album_art_url, similarity_score, lyrics_snippet}`
- Frontend: search bar, results list with:
  - Album art thumbnail
  - Title + artist
  - Similarity score
  - Clickable Spotify link (opens in Spotify app/web player)
  - Lyrics snippet (first ~100 chars, expandable)
  - Toggle: "Expand query with AI" (shows raw vs expanded results)
  - When expanded, show the generated audio description so user can see what CLAP received

#### Task 1.7: Pipeline Dashboard UI
- Single-page React app with sections:
  1. **Library Sync** — connect button, song count, status
  2. **Download** — progress table, overall bar, concurrent status
  3. **Lyrics** — progress bar, found/not found counts
  4. **Embed** — progress bar, count, ETA
  5. **Search** — query input, results with album art + Spotify links
- Each section shows state: not started / in progress / complete / error
- Use `EventSource` (SSE) hook for real-time updates
- Song table filterable/sortable, shows album art
- Each song row has a Spotify link icon → opens `https://open.spotify.com/track/{id}`
- Persist pipeline state so page refresh shows current progress

---

### Phase 2: Library Management + Playlist Creation

**Goal:** Keep the local DB in sync with Spotify liked songs (additions and removals), create Spotify playlists from search results, clusters, or nearest neighbors.

#### Task 2.1: Differential Library Sync
- `POST /api/sync` — enhanced to handle deltas, not just full re-fetch
- On sync:
  1. Fetch current liked songs from Spotify
  2. Compare against local `library.json`
  3. **New songs:** Add to library.json, queue for download + lyrics + embed
  4. **Removed songs:** Mark as removed in library.json, optionally remove from ChromaDB
  5. Return delta summary: `{added: [], removed: [], unchanged_count}`
- Frontend: shows "3 new songs added, 1 removed since last sync"
- Auto-sync option: trigger on app open or on a schedule

#### Task 2.2: Playlist Creation from Search
- `POST /api/playlist/create` — accepts `{name, spotify_ids[]}`
- Use spotipy:
  ```python
  playlist = sp.user_playlist_create(user_id, name, public=True)
  sp.playlist_add_items(playlist['id'], [uri_list])
  ```
- Frontend: "Save as Playlist" button on search results
- Auto-name: "Vibe: melancholic late night drive"
- Option to set public/private

#### Task 2.3: Multi-Song Seed Search ("Find me more like these")
- `POST /api/seed-search` — accepts `{seed_ids: string[], n_results: int, text_query?: string, text_weight?: float}`
- **Auto-detects strategy based on seed coherence:**
  1. Compute pairwise cosine similarity between all seed embeddings
  2. If avg similarity > threshold (~0.7): seeds are coherent → use **centroid averaging**
  3. If avg similarity < threshold: seeds are diverse → use **union of neighborhoods**

- **Centroid approach** (coherent seeds):
  ```python
  import numpy as np
  seed_embeddings = collection.get(ids=seed_ids, include=["embeddings"])["embeddings"]
  centroid = np.mean(seed_embeddings, axis=0).tolist()
  results = collection.query(
      query_embeddings=[centroid],
      n_results=n_results + len(seed_ids)
  )
  # filter out seeds from results
  ```

- **Union of neighborhoods** (diverse seeds):
  ```python
  from collections import defaultdict
  scores = defaultdict(float)

  for seed_id in seed_ids:
      seed_emb = collection.get(ids=[seed_id], include=["embeddings"])["embeddings"][0]
      results = collection.query(
          query_embeddings=[seed_emb],
          n_results=30
      )
      for doc_id, distance in zip(results["ids"][0], results["distances"][0]):
          if doc_id not in seed_ids:
              similarity = 1 - distance
              scores[doc_id] += similarity  # songs near MULTIPLE seeds rank highest

  ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n_results]
  ```

- **Optional text blending:** If `text_query` is provided, encode it with CLAP and blend:
  ```python
  α = text_weight  # 0.0 = audio seeds only, 1.0 = text only, 0.5 = balanced
  final_query = α * text_vector + (1 - α) * audio_centroid
  ```
  UI: slider to control α between "songs like these" and "songs matching this vibe"

- Frontend:
  - Select songs via checkboxes in library/search results → "Find similar" button
  - Shows which strategy was auto-selected (with option to override)
  - Optional text query field + blend slider
  - Results list → "Save as Playlist" (seeds + results combined)

#### Task 2.4: Playlist from Cluster (requires Phase 3 clustering)
- Same playlist creation mechanism, source is a cluster's songs
- "Export Cluster" button on each cluster panel

---

### Phase 3: Clustering & Visualization

**Goal:** Automatically discover groupings in the library and visualize the embedding space.

#### Task 3.1: HDBSCAN Clustering
- `POST /api/cluster` — runs clustering
- Extract all embeddings from ChromaDB
- Run HDBSCAN on the full 512-dimensional embeddings:
  ```python
  import hdbscan
  clusterer = hdbscan.HDBSCAN(
      min_cluster_size=5,
      min_samples=3,
      metric='euclidean',
      cluster_selection_method='eom'
  )
  labels = clusterer.fit_predict(embeddings)  # -1 = noise/outlier
  ```
- Store cluster labels back in ChromaDB metadata
- Return cluster summary: `{cluster_id, song_count, sample_songs[]}`
- Frontend: cluster list panel, expandable, rename field, "Export as Playlist" button
- Outliers (label=-1) → "Unclustered" group

#### Task 3.2: UMAP Visualization
- `POST /api/visualize/umap` — computes and caches projection
- Project 512-dim → 2D:
  ```python
  import umap
  reducer = umap.UMAP(
      n_components=2, n_neighbors=15, min_dist=0.1,
      metric='cosine', random_state=42
  )
  projection = reducer.fit_transform(embeddings)
  ```
- Return `[{spotify_id, x, y, cluster_id, title, artist, album_art_url, spotify_link}]`
- Cache result — only recompute when embeddings change
- Frontend: Plotly scatter plot
  - Dots colored by cluster
  - Hover: album art + title + artist
  - Click: open Spotify link
  - Lasso select: create playlist from selected region

#### Task 3.3: t-SNE Visualization (alternative view)
- `POST /api/visualize/tsne` — computes and caches
- Same return format as UMAP
- Frontend: toggle between UMAP and t-SNE views

### Key Principle
> **Cluster in 512-dim. Visualize in 2D. Never cluster on the 2D projection.**

---

### Phase 4: Spotify Playback Integration

**Goal:** Play songs directly from the app without leaving the browser.

#### Task 4.1: Web Playback SDK Integration
- Embed Spotify Web Playback SDK in the React frontend
- Creates a Spotify Connect device in the browser
- **Requires Spotify Premium**
- Scopes: add `streaming`, `user-read-playback-state`, `user-modify-playback-state`
- Implementation:
  ```javascript
  const player = new Spotify.Player({
      name: 'Vibe Search Player',
      getOAuthToken: cb => { cb(accessToken); }
  });
  player.connect();
  ```
- Play button on each search result / song → triggers playback
- Playback controls: play/pause, skip, seek, volume
- Queue management: "Play all results" queues the search results in order

#### Task 4.2: Player UI
- Mini player bar at bottom of dashboard
- Shows: album art, title, artist, progress bar, play/pause, skip
- Queue panel showing upcoming songs
- "Play cluster" / "Play search results" buttons

---

### Phase 5: Future Enhancements

These extend the architecture without requiring a rewrite.

#### 5A. Similarity Graph Traversal
KNN graph for DJ-style smooth playlists. Start at Song A, greedily walk to nearest unvisited neighbor. ChromaDB's `collection.query` provides KNN implicitly.

#### 5B. Interpolation / Vibe Journeys
Find songs on the path between two endpoints. Linearly interpolate N points between embeddings A and B, find nearest song to each point.

#### 5C. Taste Drift Over Time
Tag embeddings with `added_at` timestamp. Compute monthly centroids. Plot trajectory through UMAP space. Shows taste evolution.

#### 5D. Density Mapping
Kernel density estimation on 2D projection. Heatmap overlay. Dense = well-explored taste, sparse = discovery potential.

#### 5E. LLM Query Expansion
Claude API call before CLAP text encoding. "Rainy Sunday morning" → "slow tempo, minor key, acoustic guitar, soft vocals, introspective lyrics, gentle piano, ambient rain sounds." Also: generate per-song vibe descriptions from lyrics + metadata.

#### 5F. Lyrics-Aware Reranking
CLAP returns top 30 by audio similarity. Then rerank using lyrics relevance — embed lyrics with a text embedding model, score against query, blend with CLAP score. Improves results for thematic queries like "songs about heartbreak."

#### 5G. MERT Integration
Secondary embeddings for deeper music similarity (tonal, rhythmic, timbral). CLAP for text→audio, MERT for audio→audio refinement. `transformers==4.38`.

#### 5H. Hybrid Scoring
Combine CLAP similarity + cluster membership + lyrics relevance + temporal proximity + user feedback. Weighted scoring function.

---

## File Structure

```
vibe-search/
├── backend/
│   ├── main.py                     # FastAPI app, CORS, lifespan (CLAP model loading)
│   ├── config.py                   # Settings: paths, env vars, constants
│   ├── db.py                       # ChromaDB client + collection setup
│   ├── routers/
│   │   ├── sync.py                 # /api/sync endpoints (full + delta)
│   │   ├── download.py             # /api/download endpoints
│   │   ├── lyrics.py               # /api/lyrics endpoints
│   │   ├── embed.py                # /api/embed endpoints
│   │   ├── search.py               # /api/search endpoints (with LLM expansion)
│   │   ├── seed_search.py          # /api/seed-search (multi-song seed, auto-strategy)
│   │   ├── cluster.py              # /api/cluster endpoints
│   │   ├── visualize.py            # /api/visualize/umap, /api/visualize/tsne
│   │   └── playlist.py             # /api/playlist endpoints
│   ├── pipeline/
│   │   ├── spotify.py              # Spotify auth + library fetch + delta logic
│   │   ├── downloader.py           # yt-dlp wrapper with concurrency control
│   │   ├── lyrics_fetcher.py       # Genius API wrapper with caching
│   │   ├── embedder.py             # CLAP model loading + inference
│   │   ├── clustering.py           # HDBSCAN logic
│   │   └── projection.py           # UMAP + t-SNE logic
│   └── models.py                   # Pydantic models (SongState, SearchResult, etc.)
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Main layout — dashboard
│   │   ├── components/
│   │   │   ├── PipelineStatus.jsx  # 5-stage pipeline indicator
│   │   │   ├── LibrarySync.jsx     # Connect Spotify + sync + delta status
│   │   │   ├── DownloadManager.jsx # Per-song download progress
│   │   │   ├── LyricsProgress.jsx  # Lyrics fetch progress
│   │   │   ├── EmbedProgress.jsx   # Embedding progress
│   │   │   ├── SearchPanel.jsx     # Query input + results with album art + links
│   │   │   ├── SongCard.jsx        # Song display: art, title, artist, link, score
│   │   │   ├── ClusterPanel.jsx    # Cluster list + rename + export
│   │   │   ├── ScatterPlot.jsx     # UMAP/t-SNE interactive plot (Plotly)
│   │   │   └── PlaylistExport.jsx  # Export controls
│   │   ├── hooks/
│   │   │   └── useSSE.js           # Reusable SSE hook
│   │   └── api.js                  # Fetch wrappers for all backend endpoints
│   ├── package.json
│   └── vite.config.js
├── data/
│   ├── library.json                # Song metadata + state cache
│   ├── chroma/                     # ChromaDB persistent storage
│   └── projections/                # Cached UMAP/t-SNE results
├── audio/                          # Downloaded MP3 files
├── .env                            # SPOTIFY_CLIENT_ID, SPOTIFY_REDIRECT_URI, GENIUS_ACCESS_TOKEN, ANTHROPIC_API_KEY
├── requirements.txt
└── README.md
```

## Dependencies

### requirements.txt
```
fastapi
uvicorn[standard]
sse-starlette
spotipy
yt-dlp
lyricsgenius
laion-clap
chromadb
anthropic
hdbscan
umap-learn
scikit-learn
numpy
pydantic
python-dotenv
```

### Frontend (package.json)
```
react, react-dom, plotly.js, react-plotly.js, tailwindcss
```

### System
```
ffmpeg (required by yt-dlp for audio conversion)
CUDA toolkit (for CLAP GPU inference)
```

---

## API Endpoints Summary

### Pipeline (MVP)
| Method | Endpoint                  | Purpose                          |
|--------|---------------------------|----------------------------------|
| POST   | /api/sync                 | Start Spotify library sync       |
| GET    | /api/sync/stream          | SSE: sync progress               |
| POST   | /api/download             | Start batch audio download       |
| GET    | /api/download/stream      | SSE: per-song download progress  |
| POST   | /api/lyrics               | Start batch lyrics fetch         |
| GET    | /api/lyrics/stream        | SSE: lyrics fetch progress       |
| POST   | /api/embed                | Start CLAP embedding             |
| GET    | /api/embed/stream         | SSE: embedding progress          |

### Search & Analysis
| Method | Endpoint                  | Purpose                          |
|--------|---------------------------|----------------------------------|
| POST   | /api/search               | Text query → ranked results (with optional LLM expansion) |
| POST   | /api/seed-search          | Multi-song seed → find similar (auto-selects centroid vs union-of-neighborhoods) |
| POST   | /api/cluster              | Run HDBSCAN clustering           |
| GET    | /api/clusters             | Get cluster list + summaries     |
| PATCH  | /api/clusters/{id}        | Rename a cluster                 |
| POST   | /api/visualize/umap       | Compute UMAP 2D projection      |
| POST   | /api/visualize/tsne       | Compute t-SNE 2D projection     |

### Export & Playback
| Method | Endpoint                  | Purpose                          |
|--------|---------------------------|----------------------------------|
| POST   | /api/playlist/create      | Create Spotify playlist from IDs |

### Library State
| Method | Endpoint                  | Purpose                          |
|--------|---------------------------|----------------------------------|
| GET    | /api/library              | Get all songs + their states     |
| GET    | /api/stats                | Library stats (counts, etc.)     |

---

## Implementation Order

Build and test in this exact order. Each step is independently verifiable.

**MVP (Phase 1):**
1. Backend scaffolding — FastAPI app, config, ChromaDB setup, models
2. Spotify sync — OAuth flow + library fetch (with album art URLs + spotify links), save to library.json
3. Download pipeline — yt-dlp integration, 4 concurrent, status tracking
4. Lyrics pipeline — Genius API integration, 5 concurrent, store in song state
5. CLAP embedding — model loading at startup, inference, ChromaDB storage (with all metadata including lyrics)
6. Search endpoint — text query, return ranked results with album art + spotify links
7. Query expansion — LLM call (Claude API) to translate abstract queries into CLAP-friendly audio descriptions, toggleable
8. Frontend shell — React app with pipeline dashboard layout
9. Wire up SSE — progress streaming for each pipeline stage (sync, download, lyrics, embed)
10. Search UI — query bar + results display with album art, Spotify links, and expand toggle

**Phase 2 (Library + Playlists + Seed Search):**
11. Delta sync — compare local vs Spotify, handle additions/removals
12. Playlist creation — Spotify writeback from search results
13. Multi-song seed search — select songs → auto-detect centroid vs union-of-neighborhoods → find similar → optional text blending with slider

**Phase 3 (Clustering + Viz):**
14. HDBSCAN clustering — cluster on 512-dim, store labels
15. UMAP + t-SNE — 2D projections, cache results
16. Scatter plot UI — Plotly interactive visualization with album art hover
17. Playlist from cluster/lasso — export to Spotify

**Phase 4 (Playback):**
18. Web Playback SDK integration — in-browser Spotify player (Premium only)
19. Player UI — mini player, queue management
