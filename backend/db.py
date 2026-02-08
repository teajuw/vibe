import chromadb
from chromadb.config import Settings as ChromaSettings

from .config import settings


# Persistent ChromaDB client
client = chromadb.PersistentClient(
    path=str(settings.chroma_dir),
    settings=ChromaSettings(anonymized_telemetry=False)
)

# Collection for song embeddings
collection = client.get_or_create_collection(
    name="songs",
    metadata={"hnsw:space": "cosine"}
)
