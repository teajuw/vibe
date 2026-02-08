import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from sqlmodel import select

from ..config import settings
from ..database import get_session
from ..models import Song

router = APIRouter()

# Download state
_state = {
    "progress": {
        "current": 0,
        "total": 0,
        "status": "idle",
        "current_song": None,
        "success": 0,
        "failed": 0,
    },
    "active_downloads": 0,
}

# Semaphore for concurrent downloads
_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)


def _verify_download_state():
    """Sync database state with actual files on disk."""
    fixed = {"marked_done": 0, "marked_pending": 0}

    with get_session() as session:
        songs = session.exec(select(Song)).all()

        for song in songs:
            file_path = settings.audio_dir / f"{song.spotify_id}.mp3"
            file_exists = file_path.exists()

            # File exists but status isn't done → mark as done
            if file_exists and song.download_status != "done":
                db_song = session.get(Song, song.spotify_id)
                if db_song:
                    db_song.download_status = "done"
                    db_song.file_path = str(file_path)
                    db_song.updated_at = datetime.utcnow()
                    fixed["marked_done"] += 1

            # File missing but status is done → mark as pending for re-download
            elif not file_exists and song.download_status == "done":
                db_song = session.get(Song, song.spotify_id)
                if db_song:
                    db_song.download_status = "pending"
                    db_song.file_path = None
                    db_song.updated_at = datetime.utcnow()
                    fixed["marked_pending"] += 1

    return fixed


@router.post("/download/verify")
async def verify_downloads():
    """Verify download state matches files on disk."""
    fixed = _verify_download_state()
    return {"status": "verified", "fixed": fixed}


@router.post("/download")
async def start_download():
    """Start downloading audio for all pending songs."""
    # First, verify state matches disk
    _verify_download_state()

    # Get pending songs - extract to dicts to avoid detached instance errors
    with get_session() as session:
        songs = session.exec(
            select(Song).where(Song.download_status == "pending")
        ).all()
        # Extract data before session closes
        song_data = [
            {
                "spotify_id": s.spotify_id,
                "title": s.title,
                "artist": s.artist,
            }
            for s in songs
        ]

    if not song_data:
        return {"status": "no_pending", "message": "No songs to download"}

    # Reset state
    _state["progress"] = {
        "current": 0,
        "total": len(song_data),
        "status": "downloading",
        "current_song": None,
        "success": 0,
        "failed": 0,
    }
    _state["active_downloads"] = 0

    # Start downloads in background
    asyncio.create_task(_download_all(song_data))

    return {"status": "started", "total": len(song_data)}


async def _download_all(songs: list[dict]):
    """Download all songs with concurrency limit."""
    tasks = [_download_song(song) for song in songs]
    await asyncio.gather(*tasks)
    _state["progress"]["status"] = "complete"


async def _download_song(song: dict):
    """Download a single song using yt-dlp."""
    spotify_id = song["spotify_id"]
    title = song["title"]
    artist = song["artist"]

    async with _semaphore:
        _state["active_downloads"] += 1
        _state["progress"]["current_song"] = {
            "spotify_id": spotify_id,
            "title": title,
            "artist": artist,
        }

        # Update status to downloading
        with get_session() as session:
            db_song = session.get(Song, spotify_id)
            if db_song:
                db_song.download_status = "downloading"
                db_song.updated_at = datetime.utcnow()

        try:
            # Build search query
            search_query = f"ytsearch1:{artist} - {title}"
            output_path = settings.audio_dir / f"{spotify_id}.mp3"

            # Run yt-dlp
            cmd = [
                "yt-dlp",
                "-x",  # Extract audio
                "--audio-format", "mp3",
                "--audio-quality", "5",  # Medium quality, smaller files
                "-o", str(output_path).replace(".mp3", ".%(ext)s"),
                "--no-playlist",
                "--quiet",
                "--no-warnings",
                search_query,
            ]

            # Run in thread pool to not block
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=120)

            if process.returncode == 0 and output_path.exists():
                # Success
                with get_session() as session:
                    db_song = session.get(Song, spotify_id)
                    if db_song:
                        db_song.download_status = "done"
                        db_song.file_path = str(output_path)
                        db_song.updated_at = datetime.utcnow()
                _state["progress"]["success"] += 1
            else:
                # Failed
                with get_session() as session:
                    db_song = session.get(Song, spotify_id)
                    if db_song:
                        db_song.download_status = "failed"
                        db_song.updated_at = datetime.utcnow()
                _state["progress"]["failed"] += 1

        except asyncio.TimeoutError:
            with get_session() as session:
                db_song = session.get(Song, spotify_id)
                if db_song:
                    db_song.download_status = "failed"
                    db_song.updated_at = datetime.utcnow()
            _state["progress"]["failed"] += 1

        except Exception as e:
            with get_session() as session:
                db_song = session.get(Song, spotify_id)
                if db_song:
                    db_song.download_status = "failed"
                    db_song.updated_at = datetime.utcnow()
            _state["progress"]["failed"] += 1

        finally:
            _state["progress"]["current"] += 1
            _state["active_downloads"] -= 1


@router.get("/download/stream")
async def download_stream():
    """SSE stream for download progress."""
    async def event_generator():
        last_current = -1

        while True:
            progress = _state["progress"]

            # Send progress update if changed
            if progress["current"] != last_current:
                last_current = progress["current"]

                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "current": progress["current"],
                        "total": progress["total"],
                        "success": progress["success"],
                        "failed": progress["failed"],
                        "active": _state["active_downloads"],
                        "song": progress["current_song"],
                    })
                }

            # Check if complete
            if progress["status"] == "complete":
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "success": progress["success"],
                        "failed": progress["failed"],
                    })
                }
                break

            await asyncio.sleep(0.3)

    return EventSourceResponse(event_generator())
