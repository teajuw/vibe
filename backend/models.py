from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import SQLModel, Field


# ============ Database Models (SQLModel) ============

class Song(SQLModel, table=True):
    """Song record in SQLite database."""
    spotify_id: str = Field(primary_key=True)
    title: str
    artist: str
    album: str
    uri: str  # spotify:track:xxx
    added_at: datetime
    album_art_url: str
    spotify_link: str
    download_status: str = Field(default="pending")  # pending | downloading | done | failed
    embed_status: str = Field(default="pending")  # pending | processing | stored | failed
    file_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============ API Request/Response Models (Pydantic) ============

class SyncRequest(BaseModel):
    playlist_id: str


class SearchRequest(BaseModel):
    query: str
    n_results: int = 20


class SearchResult(BaseModel):
    spotify_id: str
    title: str
    artist: str
    album: str
    album_art_url: str
    spotify_link: str
    similarity_score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]


class SongResponse(BaseModel):
    """Song data for API responses."""
    spotify_id: str
    title: str
    artist: str
    album: str
    album_art_url: str
    spotify_link: str
    download_status: str
    embed_status: str

    class Config:
        from_attributes = True


class LibraryStats(BaseModel):
    total: int
    downloaded: int
    embedded: int


class LibraryResponse(BaseModel):
    songs: list[SongResponse]
    stats: LibraryStats
