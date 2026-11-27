from __future__ import annotations

from pathlib import Path
from typing import Callable

from faster_whisper import WhisperModel

from clipper.models import TranscriptSegment


def transcribe(
    audio_path: Path,
    model_name: str,
    device: str,
    compute_type: str,
    progress: Callable[[int, str], None],
) -> list[TranscriptSegment]:
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, _ = model.transcribe(
        str(audio_path),
        beam_size=5,
        vad_filter=True,
        word_timestamps=False,
    )
    transcript: list[TranscriptSegment] = []
    last_update = 0
    for segment in segments:
        transcript.append(
            TranscriptSegment(
                start=float(segment.start),
                end=float(segment.end),
                text=segment.text.strip(),
            )
        )
        if transcript and int(segment.end) >= last_update + 30:
            last_update = int(segment.end)
            progress(min(54, 24 + last_update // 30), "Transcribing speech locally")
    if not transcript:
        raise RuntimeError(
            "No speech was detected. This workflow needs speech to identify clip moments."
        )
    progress(55, "Speech transcription complete")
    return transcript
