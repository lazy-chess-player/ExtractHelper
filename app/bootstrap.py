from __future__ import annotations
import os
from pathlib import Path

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def _load_dotenv(dotenv_path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not dotenv_path.exists():
        return env
    for line in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def bootstrap() -> None:
    root = _repo_root()
    dot = _load_dotenv(root / ".env")

    for k, v in dot.items():
        os.environ.setdefault(k, v)

    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("HF_HOME", str(root / "data" / "kb" / "hf_home"))
