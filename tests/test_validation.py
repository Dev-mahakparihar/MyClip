import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clipper.validation import ValidationError, probe_media


class ValidationTests(unittest.TestCase):
    def test_validates_video_stream_and_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clip.mp4"
            path.write_bytes(b"video")
            result = subprocess.CompletedProcess(
                args=["ffprobe"],
                returncode=0,
                stdout=json.dumps(
                    {
                        "format": {"duration": "12.5"},
                        "streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
                    }
                ),
                stderr="",
            )
            with patch("clipper.validation.subprocess.run", return_value=result):
                metadata = probe_media(path)
            self.assertEqual(metadata["duration_seconds"], 12.5)

    def test_rejects_output_without_video_stream(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio.mp4"
            path.write_bytes(b"audio")
            result = subprocess.CompletedProcess(
                args=["ffprobe"],
                returncode=0,
                stdout=json.dumps(
                    {"format": {"duration": "12"}, "streams": [{"codec_type": "audio"}]}
                ),
                stderr="",
            )
            with patch("clipper.validation.subprocess.run", return_value=result):
                with self.assertRaises(ValidationError):
                    probe_media(path)

    def test_rejects_zero_duration_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.mp4"
            path.write_bytes(b"video")
            result = subprocess.CompletedProcess(
                args=["ffprobe"],
                returncode=0,
                stdout=json.dumps(
                    {
                        "format": {"duration": "0"},
                        "streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
                    }
                ),
                stderr="",
            )
            with patch("clipper.validation.subprocess.run", return_value=result):
                with self.assertRaises(ValidationError):
                    probe_media(path)


if __name__ == "__main__":
    unittest.main()
