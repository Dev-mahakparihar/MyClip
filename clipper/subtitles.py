from __future__ import annotations

from pathlib import Path

from clipper.models import TranscriptSegment


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def write_clip_subtitles(
    destination: Path,
    transcript: list[TranscriptSegment],
    clip_start: float,
    clip_end: float,
) -> None:
    lines: list[str] = []
    cue = 1
    for segment in transcript:
        start = max(clip_start, segment.start)
        end = min(clip_end, segment.end)
        if end <= start or not segment.text.strip():
            continue
        lines.extend(
            [
                str(cue),
                f"{_srt_time(start - clip_start)} --> {_srt_time(end - clip_start)}",
                segment.text.strip(),
                "",
            ]
        )
        cue += 1
    destination.write_text("\n".join(lines), encoding="utf-8")


def escape_filter_path(path: Path) -> str:
    value = path.resolve().as_posix()
    return (
        value.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )
