import unittest

from clipper.candidates import build_candidate_windows
from clipper.models import TranscriptSegment


class CandidateWindowTests(unittest.TestCase):
    def test_windows_overlap_and_cover_media(self):
        transcript = [
            TranscriptSegment(0, 10, "opening"),
            TranscriptSegment(20, 40, "middle"),
            TranscriptSegment(80, 100, "ending"),
        ]
        windows = build_candidate_windows(transcript, 100, 40, overlap=0.5)
        self.assertGreaterEqual(len(windows), 4)
        self.assertGreater(windows[0].end, windows[1].start)
        self.assertEqual(windows[-1].end, 100)
        self.assertIn("ending", windows[-1].transcript)

    def test_invalid_media_returns_no_windows(self):
        self.assertEqual(build_candidate_windows([], 0, 30), [])


if __name__ == "__main__":
    unittest.main()
