from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Spotify
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://localhost:5173/callback"

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = base_dir / "data"
    audio_dir: Path = base_dir / "audio"
    library_path: Path = data_dir / "library.json"
    chroma_dir: Path = data_dir / "chroma"

    # CLAP
    clap_checkpoint: str = "music_speech_audioset_epoch_15_esc_89.98.pt"

    # Download
    max_concurrent_downloads: int = 4

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
settings.data_dir.mkdir(exist_ok=True)
settings.audio_dir.mkdir(exist_ok=True)
