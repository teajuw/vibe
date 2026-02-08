import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import sync, download, embed, search

# Suppress some warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    init_db()

    # Load CLAP model (lazy - only when first embed is requested)
    # This avoids slow startup and memory usage if not needed
    # The model will be loaded on first /api/embed call
    print("Database initialized. CLAP model will load on first embed request.")

    yield

    # Shutdown: cleanup
    print("Shutting down...")


app = FastAPI(
    title="Vibe Search API",
    description="Semantic music search using CLAP embeddings",
    version="0.1.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(sync.router, prefix="/api", tags=["sync"])
app.include_router(download.router, prefix="/api", tags=["download"])
app.include_router(embed.router, prefix="/api", tags=["embed"])
app.include_router(search.router, prefix="/api", tags=["search"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/load-model")
async def load_clap_model():
    """Manually load the CLAP model (optional - loads automatically on first embed)."""
    if embed.get_model() is not None:
        return {"status": "already_loaded"}

    try:
        import laion_clap
        model = laion_clap.CLAP_Module(enable_fusion=False, amodel='HTSAT-base')
        model.load_ckpt()  # Downloads checkpoint if needed
        embed.set_model(model)
        return {"status": "loaded"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
