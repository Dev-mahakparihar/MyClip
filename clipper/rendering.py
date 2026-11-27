from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from clipper.models import SelectedClip, TranscriptSegment
from clipper.subtitles import escape_filter_path, write_clip_subtitles


class RenderError(RuntimeError):
    pass


def _video_filter(aspect_ratio: str) -> str | None:
    if aspect_ratio == "9:16":
        return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    if aspect_ratio == "16:9":
        return "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
    if aspect_ratio == "original":
        return None
    raise ValueError(f"Unsupported aspect ratio: {aspect_ratio}")


def render_clip(
    source: Path,
    destination: Path,
    clip: SelectedClip,
    transcript: list[TranscriptSegment],
    aspect_ratio: str,
    caption_style: str,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    filters = [_video_filter(aspect_ratio)]
    subtitle_path = destination.with_suffix(".srt")
    if caption_style != "None":
        write_clip_subtitles(subtitle_path, transcript, clip.start, clip.end)
        style = (
            "FontName=Arial,FontSize=22,Bold=0,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,"
            "Alignment=2,MarginV=70"
        )
        if caption_style == "Bold":
            style = (
                style.replace("FontSize=22", "FontSize=25")
                .replace("Bold=0", "Bold=1")
                .replace("Outline=3", "Outline=4")
            )
        filters.append(
            f"subtitles=filename='{escape_filter_path(subtitle_path)}':"
            f"force_style='{style}'"
        )
    video_filter = ",".join(item for item in filters if item)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{clip.start:.3f}",
        "-i",
        str(source),
        "-t",
        f"{clip.end - clip.start:.3f}",
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
    ]
    if video_filter:
        command.extend(["-vf", video_filter])
    command.append(str(destination))
    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=None
        )
    except FileNotFoundError as exc:
        raise RenderError("FFmpeg is missing. Install FFmpeg and retry.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RenderError(f"FFmpeg could not render {destination.name}: {detail[-1500:]}") from exc
    finally:
        if caption_style == "None":
            subtitle_path.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RenderError(f"FFmpeg returned an unexpected status for {destination.name}.")
