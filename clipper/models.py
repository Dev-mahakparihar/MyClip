from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> TranscriptSegment:
        return cls(float(value["start"]), float(value["end"]), str(value["text"]))


@dataclass(frozen=True)
class CandidateWindow:
    window_id: int
    start: float
    end: float
    transcript: str


@dataclass(frozen=True)
class ClipCandidate:
    start: float
    end: float
    score: float
    title: str
    reason: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ClipCandidate:
        return cls(
            start=float(value["start"]),
            end=float(value["end"]),
            score=float(value["score"]),
            title=str(value["title"]).strip(),
            reason=str(value["reason"]).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SelectedClip:
    start: float
    end: float
    score: float
    title: str
    reason: str
    output_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
