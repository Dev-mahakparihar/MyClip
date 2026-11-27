from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Callable

from clipper.candidates import build_candidate_windows
from clipper.config import AppConfig, load_config
from clipper.database import JobDatabase
from clipper.models import SelectedClip, TranscriptSegment
from clipper.ollama_client import OllamaError, check_ollama, rank_windows
from clipper.rendering import render_clip
from clipper.selection import select_clips
from clipper.source import SourceError, download_video, validate_youtube_video
from clipper.transcription import transcribe
from clipper.validation import probe_media


def _extract_audio(source: Path, audio_path: Path) -> None:
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=None,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg is missing. Install FFmpeg and retry.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Could not extract source audio: {(exc.stderr or '')[-1200:]}") from exc


def process_job(
    job_id: str,
    url: str,
    instruction: str,
    settings: dict,
    database: JobDatabase,
    base_config: AppConfig | None = None,
) -> None:
    config = (
        replace(base_config, output_dir=Path(settings["output_dir"]).expanduser())
        if base_config
        else load_config(settings.get("output_dir"))
    )
    job_dir = config.output_dir / job_id
    log_path = config.data_dir / f"{job_id}.log"
    logger = logging.getLogger(f"myclip.{job_id}")
    logger.setLevel(logging.INFO)
    handler: logging.FileHandler | None = None

    def update(progress: int, message: str, stage: str) -> None:
        database.update(
            job_id,
            status="running",
            progress=progress,
            stage=stage,
            message=message,
        )
        logger.info("stage=%s progress=%s message=%s", stage, progress, message)

    def source_progress(progress: int, message: str) -> None:
        update(progress, message, "download")

    try:
        job_dir.mkdir(parents=True, exist_ok=True)
        config.data_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        update(2, "Checking YouTube video availability", "url_validation")
        validated_info = validate_youtube_video(url, logger=logger)
        update(
            8,
            f"Video available: {validated_info['title']}. Checking local tools.",
            "prerequisites",
        )
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise RuntimeError("FFmpeg and FFprobe are required. Install them with `brew install ffmpeg`.")
        update(10, "Checking local Ollama model", "prerequisites")
        try:
            check_ollama(config.ollama_url, config.ollama_model)
        except OllamaError as exc:
            raise RuntimeError(str(exc)) from exc
        update(12, "Downloading source video", "download")
        source = download_video(url, job_dir, source_progress)
        if source.get("id") != validated_info["id"]:
            raise SourceError("The video ID changed between validation and download.")
        metadata = probe_media(source["path"])
        duration = float(metadata["duration_seconds"])
        if source["duration"] and duration > source["duration"] + 15:
            raise RuntimeError("Downloaded source metadata did not match the media duration.")
        database.update(job_id, source_path=str(source["path"]))

        update(21, "Preparing audio for local transcription", "transcription")
        audio_path = job_dir / "transcription.wav"
        _extract_audio(source["path"], audio_path)

        def transcription_progress(progress: int, message: str) -> None:
            update(progress, message, "transcription")

        transcript = transcribe(
            audio_path,
            config.whisper_model,
            config.whisper_device,
            config.whisper_compute_type,
            transcription_progress,
        )
        transcript_path = job_dir / "transcript.json"
        transcript_path.write_text(
            json.dumps(
                [segment.__dict__ for segment in transcript],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        database.update(job_id, transcript_path=str(transcript_path))
        audio_path.unlink(missing_ok=True)

        windows = build_candidate_windows(
            transcript, duration, float(settings["max_duration"])
        )
        if not windows:
            raise RuntimeError("No transcript candidate windows could be created.")
        update(57, f"Analyzing {len(windows)} transcript windows", "analysis")
        candidates = rank_windows(
            config.ollama_url,
            config.ollama_model,
            instruction,
            windows,
            float(settings["min_duration"]),
            float(settings["max_duration"]),
            int(settings["clip_count"]),
            lambda progress, message: update(progress, message, "analysis"),
        )
        clips = select_clips(
            candidates,
            duration,
            float(settings["min_duration"]),
            float(settings["max_duration"]),
            int(settings["clip_count"]),
        )
        if not clips:
            raise RuntimeError(
                "The local model found no candidates that met your duration and "
                "non-overlap requirements. Try broader instructions or wider duration limits."
            )
        update(72, f"Rendering {len(clips)} clips", "render")
        exported: list[SelectedClip] = []
        for index, clip in enumerate(clips, start=1):
            output_path = job_dir / f"clip-{index:03}.mp4"
            render_clip(
                source["path"],
                output_path,
                clip,
                transcript,
                str(settings["aspect_ratio"]),
                str(settings["caption_style"]),
            )
            exported.append(
                SelectedClip(
                    start=clip.start,
                    end=clip.end,
                    score=clip.score,
                    title=clip.title,
                    reason=clip.reason,
                    output_path=str(output_path),
                )
            )
            update(
                72 + int(18 * index / len(clips)),
                f"Rendered clip {index} of {len(clips)}",
                "render",
            )

        for index, clip in enumerate(exported, start=1):
            update(90 + int(9 * index / len(exported)), f"Validating clip {index}", "validation")
            exported_duration = float(
                probe_media(Path(clip.output_path))["duration_seconds"]
            )
            expected = clip.end - clip.start
            if abs(exported_duration - expected) > max(2.0, expected * 0.08):
                raise RuntimeError(
                    f"Output validation failed for {Path(clip.output_path).name}: "
                    "exported duration differs from the selected timestamps."
                )

        database.update(
            job_id,
            status="completed",
            stage="complete",
            progress=100,
            message=f"Completed {len(exported)} clips from {source['title']}",
            clips_json=json.dumps([clip.to_dict() for clip in exported]),
            error=None,
        )
        logger.info("Job completed successfully with %d clips", len(exported))
    except Exception as exc:
        logger.exception("Job failed")
        database.update(
            job_id,
            status="failed",
            stage="failed",
            message="Processing failed",
            error=f"{exc}\nLog: {log_path}",
        )
    finally:
        if handler is not None:
            handler.close()
            logger.removeHandler(handler)
