
from __future__ import annotations

import math

from clipper.models import ClipCandidate, SelectedClip


def select_clips(
    candidates: list[ClipCandidate],
    media_duration: float,
    min_duration: float,
    max_duration: float,
    requested_count: int,
) -> list[SelectedClip]:
    if media_duration <= 0 or min_duration <= 0 or max_duration < min_duration:
        raise ValueError("Invalid media or clip duration limits.")
    if requested_count < 1:
        raise ValueError("At least one clip must be requested.")

    valid: list[ClipCandidate] = []
    seen: set[tuple[float, float, str]] = set()

    for candidate in candidates:
        if not all(
            math.isfinite(value)
            for value in (candidate.start, candidate.end, candidate.score)
        ):
            continue

        start = max(0.0, candidate.start)
        end = min(media_duration, candidate.end)
        duration = end - start
        title = candidate.title.strip()[:120]
        reason = candidate.reason[:500]

        if not title or not min_duration <= duration <= max_duration:
            continue

        # Remove exact duplicate candidates.
        key = (round(start, 1), round(end, 1), title.casefold())
        if key in seen:
            continue
        seen.add(key)

        valid.append(
            ClipCandidate(
                start=start,
                end=end,
                score=max(0.0, min(100.0, candidate.score)),
                title=title,
                reason=reason,
            )
        )

    valid.sort(key=lambda candidate: (-candidate.score, candidate.start))

    selected: list[SelectedClip] = []

    for candidate in valid:
        candidate_duration = candidate.end - candidate.start
        overlaps_existing = False

        for clip in selected:
            overlap = max(
                0.0,
                min(candidate.end, clip.end) - max(candidate.start, clip.start),
            )

            shorter_duration = min(
                candidate_duration, clip.end - clip.start
            )

            # Reject overlapping clips and clips that substantially
            # repeat the same time range.
            if overlap > 0 or (
                shorter_duration > 0
                and overlap / shorter_duration >= 0.5
            ):
                overlaps_existing = True
                break

            # Avoid clips clustered around almost the same moment.
            if abs(candidate.start - clip.start) < 5.0:
                overlaps_existing = True
                break

        if overlaps_existing:
            continue

        selected.append(
            SelectedClip(
                start=candidate.start,
                end=candidate.end,
                score=candidate.score,
                title=candidate.title,
                reason=candidate.reason,
            )
        )

        if len(selected) >= requested_count:
            break

    return sorted(selected, key=lambda clip: clip.start)
