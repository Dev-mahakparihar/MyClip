from __future__ import annotations

import json
import time
from typing import Any, Callable

import requests

from clipper.models import CandidateWindow, ClipCandidate


class OllamaError(RuntimeError):
    pass


def _normalize_model_name(name: str) -> str:
    value = str(name).strip()
    if value.startswith("library/"):
        value = value.split("/", 1)[1]
    return value


def _model_matches(model: str, candidate: Any) -> bool:
    normalized = _normalize_model_name(candidate)
    requested = model.strip()
    if normalized == requested:
        return True
    if normalized == f"{requested}:latest":
        return True
    if ":" in requested and normalized == requested.split(":", 1)[0]:
        return True
    return False


def check_ollama(base_url: str, model: str) -> None:
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
    except requests.RequestException as exc:
        raise OllamaError(
            f"Cannot connect to Ollama at {base_url}. Start Ollama and retry."
        ) from exc

    if any(_model_matches(model, item.get("name")) for item in models):
        return
    raise OllamaError(
        f"Ollama model '{model}' is not installed. Pull it with `ollama pull {model}` "
        "and retry. MyClip does not download AI models automatically while processing."
    )


def _parse_response(response_text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise OllamaError("Ollama returned invalid JSON while ranking clip moments.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
        raise OllamaError("Ollama response must contain a JSON candidates array.")
    return data["candidates"]


def rank_windows(
    base_url: str,
    model: str,
    instruction: str,
    windows: list[CandidateWindow],
    min_duration: float,
    max_duration: float,
    requested_count: int,
    progress: Callable[[int, str], None],
) -> list[ClipCandidate]:
    check_ollama(base_url, model)
    batch_size = 3
    batches = [
      windows[i : i + batch_size]
      for i in range(0, len(windows), batch_size)
]
    candidates: list[ClipCandidate] = []
    for batch_index, batch in enumerate(batches):
        prompt_windows = [
            {
                "id": window.window_id,
                "window_start": window.start,
                "window_end": window.end,
                "transcript": window.transcript,
            }
            for window in batch
            if window.transcript.strip()
        ]
        if not prompt_windows:
            continue
        prompt = {
            
                "task": (
                    "You are an expert short-form video editor. Select the strongest "
                    "moments for standalone short clips using only the provided transcript. "
                    "Follow the user's instructions and topic closely. "
                    "Prioritize moments in this order: "
                    "(1) an immediately interesting hook, surprising statement, funny exchange, "
                    "strong opinion, useful insight, or clear dramatic tension; "
                    "(2) enough context for a new viewer to understand what is happening; "
                    "(3) a satisfying payoff, punchline, reveal, answer, or completed thought. "
                    "Prefer moments that start close to the interesting part and end after "
                    "the payoff. Avoid long introductions, greetings, pauses, repeated ideas, "
                    "incomplete sentences, unexplained references, and ordinary conversation "
                    "unless it directly matches the user's instructions. "
                    "Do not invent events or infer emotions, gameplay, facial expressions, "
                    "kills, wins, or visual reactions from dialogue alone. "
                    "Score each candidate from 0 to 100: reward hook strength, coherence, "
                    "payoff, relevance, and standalone value. Penalize filler, missing context, "
                    "and weak or unfinished endings. Do not give high scores merely because "
                    "a clip contains many words. Prefer genuinely strong moments over filling "
                    "the requested count with weak ones. Choose different moments when possible. "
                    "Return only valid JSON in this format: "
                    "{\"candidates\":[{\"window_id\":0,\"start\":0.0,\"end\":30.0,"
                    "\"score\":0.0,\"title\":\"...\",\"reason\":\"...\"}]}. "
                    "Timestamps must be absolute seconds and remain inside the specified window. "
                    "Each clip must meet the requested minimum and maximum duration. "
                    "Return at most the requested number of candidates for this batch."
                ),

            "user_instructions": instruction,
            "min_duration_seconds": min_duration,
            "max_duration_seconds": max_duration,
            "requested_total_clips": requested_count,
            "windows": prompt_windows,
        }
        for attempt in range(2):
            try:
                response = requests.post(
                    f"{base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": json.dumps(prompt, ensure_ascii=False),
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.2},
                    },
                    timeout=(10, 300),
                )
                response.raise_for_status()
                payload = response.json()
                raw_candidates = _parse_response(payload.get("response", ""))
                by_id = {window.window_id: window for window in batch}
                for raw in raw_candidates:
                    if not isinstance(raw, dict):
                        continue
                    try:
                        candidate = ClipCandidate.from_dict(raw)
                        window = by_id[int(raw["window_id"])]
                    except (KeyError, TypeError, ValueError):
                        continue
                    if not (
                        window.start <= candidate.start < candidate.end <= window.end
                    ):
                        continue
                    candidates.append(candidate)
                break
            except (requests.RequestException, ValueError) as exc:
                if attempt == 0 and isinstance(exc, requests.RequestException):
                    time.sleep(1)
                    continue
                raise OllamaError(
                    f"Ollama could not rank transcript window batch {batch_index + 1}: {exc}"
                ) from exc
            except OllamaError:
                raise
        progress(
            60 + int(10 * (batch_index + 1) / max(1, len(batches))),
            f"Analyzing transcript moments ({batch_index + 1}/{len(batches)})",
        )
    return candidates
