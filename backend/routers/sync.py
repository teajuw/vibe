import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from sqlmodel import select

from ..config import settings
from ..database import get_session
from ..models import Song, SyncRequest

router = APIRouter()

# In-memory state for auth and sync progress
_state = {
    "access_token": None,
    "progress": {"current": 0, "total": 0, "status": "idle", "latest_song": None},
}


def get_spotify_oauth() -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
        redirect_uri=settings.spotify_redirect_uri,
        scope="playlist-read-private playlist-read-collaborative user-library-read",
    )


@router.get("/auth/url")
async def get_auth_url():
    """Get Spotify OAuth URL for user authorization."""
    oauth = get_spotify_oauth()
    auth_url = oauth.get_authorize_url()
    return {"url": auth_url}


@router.get("/auth/callback")
async def auth_callback(code: str = Query(...)):
    """Exchange authorization code for access token."""
    oauth = get_spotify_oauth()
    try:
        token_info = oauth.get_access_token(code, as_dict=True)
        _state["access_token"] = token_info["access_token"]
        return {"status": "authenticated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/auth/status")
async def auth_status():
    """Check if user is authenticated."""
    return {"authenticated": _state["access_token"] is not None}


@router.post("/sync")
async def start_sync(request: SyncRequest):
    """Start syncing tracks from a Spotify playlist."""
    if not _state["access_token"]:
        raise HTTPException(status_code=401, detail="Not authenticated with Spotify")

    # Reset progress
    _state["progress"] = {"current": 0, "total": 0, "status": "syncing", "latest_song": None}

    # Start sync in background
    asyncio.create_task(_sync_playlist(request.playlist_id))

    return {"status": "started", "playlist_id": request.playlist_id}


async def _sync_playlist(playlist_id: str):
    """Fetch all tracks from a playlist and save to database."""
    try:
        sp = spotipy.Spotify(auth=_state["access_token"])

        # Get playlist info first to get total
        playlist = sp.playlist(playlist_id, fields="tracks.total,name")
        total = playlist["tracks"]["total"]
        _state["progress"]["total"] = total

        # Paginate through tracks
        offset = 0
        limit = 50
        synced_count = 0

        while offset < total:
            results = sp.playlist_tracks(
                playlist_id,
                offset=offset,
                limit=limit,
                fields="items(added_at,track(id,name,artists,album(name,images),uri))"
            )

            with get_session() as session:
                for item in results["items"]:
                    track = item["track"]
                    if not track or not track["id"]:  # Skip local files
                        continue

                    # Check if song already exists
                    existing = session.get(Song, track["id"])
                    if existing:
                        synced_count += 1
                        _state["progress"]["current"] = synced_count
                        continue

                    # Get album art (largest available)
                    album_art_url = ""
                    if track["album"]["images"]:
                        album_art_url = track["album"]["images"][0]["url"]

                    # Parse added_at timestamp
                    added_at = datetime.fromisoformat(item["added_at"].replace("Z", "+00:00"))

                    # Create new song record
                    song = Song(
                        spotify_id=track["id"],
                        title=track["name"],
                        artist=", ".join(a["name"] for a in track["artists"]),
                        album=track["album"]["name"],
                        uri=track["uri"],
                        added_at=added_at,
                        album_art_url=album_art_url,
                        spotify_link=f"https://open.spotify.com/track/{track['id']}",
                    )

                    session.add(song)
                    synced_count += 1

                    _state["progress"]["current"] = synced_count
                    _state["progress"]["latest_song"] = {"title": song.title, "artist": song.artist}

            offset += limit
            await asyncio.sleep(0.1)  # Small delay to avoid rate limits

        _state["progress"]["status"] = "complete"

    except Exception as e:
        _state["progress"]["status"] = f"error: {str(e)}"


@router.post("/sync/liked")
async def start_sync_liked():
    """Start syncing user's liked songs."""
    if not _state["access_token"]:
        raise HTTPException(status_code=401, detail="Not authenticated with Spotify")

    # Reset progress
    _state["progress"] = {"current": 0, "total": 0, "status": "syncing", "latest_song": None}

    # Start sync in background
    asyncio.create_task(_sync_liked_songs())

    return {"status": "started", "source": "liked_songs"}


async def _sync_liked_songs():
    """Fetch all liked songs and save to database."""
    try:
        sp = spotipy.Spotify(auth=_state["access_token"])

        # Get total count first
        initial = sp.current_user_saved_tracks(limit=1)
        total = initial["total"]
        _state["progress"]["total"] = total

        # Paginate through liked songs
        offset = 0
        limit = 50
        synced_count = 0

        while offset < total:
            results = sp.current_user_saved_tracks(offset=offset, limit=limit)

            with get_session() as session:
                for item in results["items"]:
                    track = item["track"]
                    if not track or not track["id"]:  # Skip local files
                        continue

                    # Check if song already exists
                    existing = session.get(Song, track["id"])
                    if existing:
                        synced_count += 1
                        _state["progress"]["current"] = synced_count
                        continue

                    # Get album art (largest available)
                    album_art_url = ""
                    if track["album"]["images"]:
                        album_art_url = track["album"]["images"][0]["url"]

                    # Parse added_at timestamp
                    added_at = datetime.fromisoformat(item["added_at"].replace("Z", "+00:00"))

                    # Create new song record
                    song = Song(
                        spotify_id=track["id"],
                        title=track["name"],
                        artist=", ".join(a["name"] for a in track["artists"]),
                        album=track["album"]["name"],
                        uri=track["uri"],
                        added_at=added_at,
                        album_art_url=album_art_url,
                        spotify_link=f"https://open.spotify.com/track/{track['id']}",
                    )

                    session.add(song)
                    synced_count += 1

                    _state["progress"]["current"] = synced_count
                    _state["progress"]["latest_song"] = {"title": song.title, "artist": song.artist}

            offset += limit
            await asyncio.sleep(0.1)  # Small delay to avoid rate limits

        _state["progress"]["status"] = "complete"

    except Exception as e:
        _state["progress"]["status"] = f"error: {str(e)}"


@router.get("/sync/stream")
async def sync_stream():
    """SSE stream for sync progress."""
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
                        "song": progress["latest_song"]
                    })
                }

            # Check if complete or error
            if progress["status"] == "complete":
                yield {
                    "event": "complete",
                    "data": json.dumps({"count": progress["current"]})
                }
                break
            elif progress["status"].startswith("error"):
                yield {
                    "event": "error",
                    "data": json.dumps({"message": progress["status"]})
                }
                break

            await asyncio.sleep(0.2)

    return EventSourceResponse(event_generator())
