import math
import unittest

from clipper.models import ClipCandidate
from clipper.selection import select_clips


class SelectionTests(unittest.TestCase):
    def test_selects_highest_scoring_non_overlapping_candidates(self):
        candidates = [
            ClipCandidate(10, 40, 70, "first", "evidence"),
            ClipCandidate(20, 50, 99, "overlap", "evidence"),
            ClipCandidate(60, 90, 80, "second", "evidence"),
        ]
        selected = select_clips(candidates, 100, 20, 40, 5)
        self.assertEqual([clip.title for clip in selected], ["overlap", "second"])

    def test_rejects_invalid_duration_and_clamps_to_media_bounds(self):
        candidates = [
            ClipCandidate(-4, 26, 90, "clamped", "evidence"),
            ClipCandidate(10, 25, 100, "too short", "evidence"),
            ClipCandidate(20, 70, 100, "too long", "evidence"),
            ClipCandidate(70, 200, 80, "outside", "evidence"),
            ClipCandidate(30, 60, math.nan, "nan score", "evidence"),
        ]
        selected = select_clips(candidates, 100, 20, 40, 10)
        self.assertEqual([(clip.start, clip.end) for clip in selected], [(0, 26), (70, 100)])

    def test_obeys_requested_clip_count(self):
        candidates = [
            ClipCandidate(0, 20, 80, "one", ""),
            ClipCandidate(30, 50, 70, "two", ""),
            ClipCandidate(60, 80, 60, "three", ""),
        ]
        self.assertEqual(len(select_clips(candidates, 100, 10, 30, 2)), 2)

    def test_rejects_invalid_duration_limits(self):
        with self.assertRaises(ValueError):
            select_clips([], 0, 10, 20, 1)
        with self.assertRaises(ValueError):
            select_clips([], 100, 30, 20, 1)


if __name__ == "__main__":
    unittest.main()
