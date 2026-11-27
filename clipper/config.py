from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "MyClip"
DEFAULT_MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://127.0.0.1:11434"


@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    output_dir: Path
    ollama_url: str = OLLAMA_URL
    ollama_model: str = DEFAULT_MODEL
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "jobs.sqlite3"


def load_config(output_dir: str | Path | None = None) -> AppConfig:
    support_dir = Path(
        os.environ.get(
            "MYCLIP_DATA_DIR",
            Path.home() / "Library" / "Application Support" / APP_NAME,
        )
    ).expanduser()
    default_output = Path(
        os.environ.get("MYCLIP_OUTPUT_DIR", Path.home() / "Movies" / APP_NAME)
    ).expanduser()
    return AppConfig(
        data_dir=support_dir,
        output_dir=Path(output_dir).expanduser() if output_dir else default_output,
        ollama_url=os.environ.get("OLLAMA_HOST", OLLAMA_URL).rstrip("/"),
        ollama_model=os.environ.get("MYCLIP_OLLAMA_MODEL", DEFAULT_MODEL),
        whisper_model=os.environ.get("MYCLIP_WHISPER_MODEL", "small"),
        whisper_device=os.environ.get("MYCLIP_WHISPER_DEVICE", "cpu"),
        whisper_compute_type=os.environ.get("MYCLIP_WHISPER_COMPUTE_TYPE", "int8"),
    )
