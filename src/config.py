from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

try:
    from dotenv import load_dotenv as _load_dotenv
except ModuleNotFoundError:
    _load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parents[1]
MATERIALS_DIR = ROOT_DIR / "materials"
VECTOR_STORE_DIR = ROOT_DIR / "vector_store"
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


@dataclass(frozen=True)
class AppConfig:
    api_key: str
    base_url: str
    model: str
    temperature: float = 0.2
    top_k: int = 5
    min_similarity: float = 0.08
    chunk_size: int = 420
    chunk_overlap: int = 80

    @property
    def llm_ready(self) -> bool:
        return bool(self.api_key.strip())


def load_config() -> AppConfig:
    env_path = ROOT_DIR / ".env"
    if _load_dotenv:
        _load_dotenv(env_path, override=True)
    elif env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip('"').strip("'")
    return AppConfig(
        api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
    )


def ensure_project_dirs() -> None:
    MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
