from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class ValidationError(RuntimeError):
    pass


def probe_media(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValidationError(f"Media file is missing or empty: {path.name}")
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,width,height",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        metadata = json.loads(result.stdout)
    except FileNotFoundError as exc:
        raise ValidationError("FFprobe is missing. Install FFmpeg and retry.") from exc
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise ValidationError(f"FFprobe could not validate {path.name}: {exc}") from exc
    streams = metadata.get("streams", [])
    if not any(stream.get("codec_type") == "video" for stream in streams):
        raise ValidationError(f"No video stream found in {path.name}.")
    try:
        duration = float(metadata["format"]["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(f"FFprobe returned no valid duration for {path.name}.") from exc
    if duration <= 0:
        raise ValidationError(f"Video duration must be positive for {path.name}.")
    metadata["duration_seconds"] = duration
    return metadata
