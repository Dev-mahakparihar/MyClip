import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clipper.config import AppConfig
from clipper.jobs import JobManager


class JobManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        config = AppConfig(data_dir=root / "data", output_dir=root / "output")
        self.manager = JobManager(config)
        self.settings = {
            "clip_count": 2,
            "min_duration": 10,
            "max_duration": 30,
            "aspect_ratio": "original",
            "caption_style": "Standard",
            "output_dir": str(root / "output"),
        }

    def tearDown(self):
        self.manager.executor.shutdown(wait=True)
        self.temp_dir.cleanup()

    def test_repeated_submission_reuses_active_job(self):
        with patch.object(self.manager.executor, "submit") as submit:
            first_id, first_created = self.manager.submit(
                "https://youtu.be/abc123xyz89", "find highlights", self.settings
            )
            second_id, second_created = self.manager.submit(
                "https://youtu.be/abc123xyz89", "find highlights", self.settings
            )

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first_id, second_id)
        submit.assert_called_once()

    def test_unexpected_worker_exception_marks_job_failed(self):
        with patch.object(self.manager.executor, "submit"):
            job_id, _ = self.manager.submit(
                "https://youtu.be/abc123xyz89", "find highlights", self.settings
            )

        with patch("clipper.jobs.process_job", side_effect=RuntimeError("worker crashed")), \
             patch.object(self.manager.logger, "exception"):
            self.manager._run_job(
                job_id,
                "https://youtu.be/abc123xyz89",
                "find highlights",
                self.settings,
            )

        job = self.manager.database.get(job_id)
        self.assertEqual(job["status"], "failed")
        self.assertEqual(job["stage"], "failed")
        self.assertIn("worker crashed", job["error"])


if __name__ == "__main__":
    unittest.main()
