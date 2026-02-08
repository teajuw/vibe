from fastapi import APIRouter, HTTPException
from sqlmodel import select, func

from ..database import get_session
from ..db import collection
from ..models import Song, SearchRequest, SearchResponse, SearchResult, LibraryResponse, LibraryStats, SongResponse
from .embed import get_model, _load_model

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search for songs by vibe/text query using CLAP embeddings."""
    # Ensure model is loaded
    model = get_model()
    if model is None:
        if not _load_model():
            raise HTTPException(status_code=503, detail="CLAP model not available")
        model = get_model()

    # Check if we have any embeddings
    if collection.count() == 0:
        return SearchResponse(results=[])

    try:
        # Encode text query with CLAP
        text_embedding = model.get_text_embedding([request.query], use_tensor=False)
        query_vector = text_embedding[0].tolist()

        # Query ChromaDB for nearest neighbors
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=min(request.n_results, collection.count()),
            include=["metadatas", "distances"]
        )

        # Format results
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, spotify_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                # ChromaDB returns distance, convert to similarity (1 - distance for cosine)
                distance = results["distances"][0][i]
                similarity = 1 - distance  # Cosine distance to similarity

                search_results.append(SearchResult(
                    spotify_id=spotify_id,
                    title=metadata.get("title", ""),
                    artist=metadata.get("artist", ""),
                    album=metadata.get("album", ""),
                    album_art_url=metadata.get("album_art_url", ""),
                    spotify_link=metadata.get("spotify_link", ""),
                    similarity_score=round(similarity, 4),
                ))

        return SearchResponse(results=search_results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.get("/library", response_model=LibraryResponse)
async def get_library():
    """Get all songs and their current pipeline status."""
    with get_session() as session:
        # Get all songs
        songs = session.exec(select(Song)).all()

        # Calculate stats
        total = len(songs)
        downloaded = sum(1 for s in songs if s.download_status == "done")
        embedded = sum(1 for s in songs if s.embed_status == "stored")

        return LibraryResponse(
            songs=[SongResponse.model_validate(s) for s in songs],
            stats=LibraryStats(total=total, downloaded=downloaded, embedded=embedded)
        )
