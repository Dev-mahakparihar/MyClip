import json
import subprocess
import unittest
from unittest.mock import patch

from clipper.source import SourceError, validate_youtube_video


class YouTubeValidationTests(unittest.TestCase):
    URL = "https://www.youtube.com/watch?v=abc123xyz89"

    def test_success_returns_metadata_without_downloading_video(self):
        result = subprocess.CompletedProcess(
            args=["yt-dlp"],
            returncode=0,
            stdout=json.dumps({"id": "abc123xyz89", "title": "Public test", "duration": 30}),
            stderr="",
        )
        with patch("clipper.source.subprocess.run", return_value=result) as run:
            metadata = validate_youtube_video(self.URL)

        self.assertEqual(metadata["id"], "abc123xyz89")
        command = run.call_args.args[0]
        self.assertIn("--skip-download", command)
        self.assertIn("--dump-single-json", command)
        self.assertEqual(run.call_args.kwargs["timeout"], 20)

    def test_timeout_is_reported(self):
        with patch(
            "clipper.source.subprocess.run",
            side_effect=subprocess.TimeoutExpired("yt-dlp", 20),
        ) as run:
            with self.assertRaisesRegex(SourceError, "timed out"):
                validate_youtube_video(self.URL)
        self.assertEqual(run.call_args.kwargs["timeout"], 20)

    def test_subprocess_failure_reports_network_error(self):
        result = subprocess.CompletedProcess(
            args=["yt-dlp"],
            returncode=1,
            stdout="",
            stderr="Unable to download webpage: <urlopen error Network is unreachable>",
        )
        with patch("clipper.source.subprocess.run", return_value=result):
            with self.assertRaisesRegex(SourceError, "network error"):
                validate_youtube_video(self.URL)

    def test_nonzero_subprocess_exit_is_reported(self):
        result = subprocess.CompletedProcess(
            args=["yt-dlp"],
            returncode=1,
            stdout="",
            stderr="ERROR: Unsupported URL",
        )
        with patch("clipper.source.subprocess.run", return_value=result):
            with self.assertRaisesRegex(SourceError, "could not validate"):
                validate_youtube_video(self.URL)

    def test_unavailable_video_reports_access_restriction(self):
        result = subprocess.CompletedProcess(
            args=["yt-dlp"],
            returncode=1,
            stdout="",
            stderr="ERROR: [youtube] abc123xyz89: Private video",
        )
        with patch("clipper.source.subprocess.run", return_value=result):
            with self.assertRaisesRegex(SourceError, "unavailable or access-restricted"):
                validate_youtube_video(self.URL)

    def test_invalid_url_does_not_start_network_validation(self):
        with patch("clipper.source.subprocess.run") as run:
            with self.assertRaisesRegex(SourceError, "valid public YouTube video URL"):
                validate_youtube_video("https://example.com/video")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
