import asyncio
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from sqlmodel import select

from ..config import settings
from ..database import get_session
from ..db import collection
from ..models import Song

router = APIRouter()

# Embed state
_state = {
    "progress": {
        "current": 0,
        "total": 0,
        "status": "idle",
        "current_song": None,
    },
    "model": None,  # CLAP model loaded at startup
}

# Thread pool for CPU-bound CLAP inference
_executor = ThreadPoolExecutor(max_workers=1)


def set_model(model):
    """Set the CLAP model (called from main.py lifespan)."""
    _state["model"] = model


def get_model():
    """Get the CLAP model."""
    return _state["model"]


def _load_model():
    """Load CLAP model if not already loaded."""
    if _state["model"] is not None:
        return True

    try:
        import laion_clap
        print("Loading CLAP model...")
        model = laion_clap.CLAP_Module(enable_fusion=False)
        model.load_ckpt()  # Downloads checkpoint if needed (~600MB)
        _state["model"] = model
        print("CLAP model loaded successfully")
        return True
    except Exception as e:
        print(f"Failed to load CLAP model: {e}")
        return False


@router.post("/embed")
async def start_embed():
    """Start generating CLAP embeddings for downloaded songs."""
    # Auto-load model if needed
    if _state["model"] is None:
        if not _load_model():
            raise HTTPException(status_code=503, detail="Failed to load CLAP model")

    # Get songs ready for embedding - extract to dicts to avoid DetachedInstanceError
    with get_session() as session:
        songs = session.exec(
            select(Song).where(
                Song.download_status == "done",
                Song.embed_status == "pending"
            )
        ).all()
        # Extract data before session closes
        song_data = [
            {
                "spotify_id": s.spotify_id,
                "title": s.title,
                "artist": s.artist,
                "album": s.album,
                "album_art_url": s.album_art_url,
                "spotify_link": s.spotify_link,
                "file_path": s.file_path,
            }
            for s in songs
        ]

    if not song_data:
        return {"status": "no_pending", "message": "No songs to embed"}

    # Reset state
    _state["progress"] = {
        "current": 0,
        "total": len(song_data),
        "status": "embedding",
        "current_song": None,
    }

    # Start embedding in background
    asyncio.create_task(_embed_all(song_data))

    return {"status": "started", "total": len(songs)}


async def _embed_all(songs: list[dict]):
    """Embed all songs sequentially (GPU is the bottleneck)."""
    loop = asyncio.get_event_loop()

    for song in songs:
        spotify_id = song["spotify_id"]
        _state["progress"]["current_song"] = {
            "spotify_id": spotify_id,
            "title": song["title"],
            "artist": song["artist"],
        }

        # Update status to processing
        with get_session() as session:
            db_song = session.get(Song, spotify_id)
            if db_song:
                db_song.embed_status = "processing"
                db_song.updated_at = datetime.utcnow()

        try:
            # Run CLAP inference in thread pool (CPU/GPU bound)
            embedding = await loop.run_in_executor(
                _executor,
                _generate_embedding,
                song["file_path"]
            )

            if embedding is not None:
                # Store in ChromaDB
                collection.upsert(
                    ids=[spotify_id],
                    embeddings=[embedding],
                    metadatas=[{
                        "title": song["title"],
                        "artist": song["artist"],
                        "album": song["album"],
                        "album_art_url": song["album_art_url"],
                        "spotify_link": song["spotify_link"],
                    }]
                )

                # Update SQLite
                with get_session() as session:
                    db_song = session.get(Song, spotify_id)
                    if db_song:
                        db_song.embed_status = "stored"
                        db_song.updated_at = datetime.utcnow()
            else:
                with get_session() as session:
                    db_song = session.get(Song, spotify_id)
                    if db_song:
                        db_song.embed_status = "failed"
                        db_song.updated_at = datetime.utcnow()

        except Exception as e:
            print(f"Embed error for {spotify_id}: {e}")
            with get_session() as session:
                db_song = session.get(Song, spotify_id)
                if db_song:
                    db_song.embed_status = "failed"
                    db_song.updated_at = datetime.utcnow()

        _state["progress"]["current"] += 1

    _state["progress"]["status"] = "complete"


def _generate_embedding(file_path: str) -> list[float] | None:
    """Generate CLAP embedding for an audio file (runs in thread pool)."""
    model = _state["model"]
    if model is None:
        return None

    try:
        # CLAP expects a list of file paths
        embeddings = model.get_audio_embedding_from_filelist([file_path], use_tensor=False)
        # Returns shape (1, 512), extract first row
        return embeddings[0].tolist()
    except Exception as e:
        print(f"CLAP embedding error for {file_path}: {e}")
        return None


@router.get("/embed/stream")
async def embed_stream():
    """SSE stream for embedding progress."""
    async def event_generator():
        last_current = -1

        while True:
            progress = _state["progress"]

            if progress["current"] != last_current:
                last_current = progress["current"]

                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "current": progress["current"],
                        "total": progress["total"],
                        "song": progress["current_song"],
                    })
                }

            if progress["status"] == "complete":
                yield {
                    "event": "complete",
                    "data": json.dumps({"count": progress["current"]})
                }
                break

            await asyncio.sleep(0.3)

    return EventSourceResponse(event_generator())
