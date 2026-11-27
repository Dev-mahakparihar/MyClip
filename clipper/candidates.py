from __future__ import annotations

from clipper.models import CandidateWindow, TranscriptSegment


def build_candidate_windows(
    transcript: list[TranscriptSegment],
    media_duration: float,
    max_clip_duration: float,
    overlap: float = 0.5,
) -> list[CandidateWindow]:
    if media_duration <= 0 or max_clip_duration <= 0:
        return []
    window_duration = min(max_clip_duration, media_duration)
    stride = max(1.0, window_duration * (1.0 - overlap))
    starts: list[float] = []
    start = 0.0
    while start < media_duration:
        end = min(media_duration, start + window_duration)
        if end - start > 0:
            starts.append(start)
        if end >= media_duration:
            break
        start += stride
    if not starts:
        starts.append(0.0)
    windows: list[CandidateWindow] = []
    for index, start in enumerate(starts):
        end = min(media_duration, start + window_duration)
        lines = [
            f"[{segment.start:.2f}-{segment.end:.2f}] {segment.text}"
            for segment in transcript
            if segment.end > start and segment.start < end
        ]
        windows.append(
            CandidateWindow(index, start, end, "\n".join(lines))
        )
    return windows
