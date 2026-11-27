import unittest
from unittest.mock import Mock, patch

from clipper.ollama_client import OllamaError, check_ollama


class OllamaClientTests(unittest.TestCase):
    def test_reports_missing_model_without_blocking_to_pull_it(self):
        first = Mock(status_code=200)
        first.json.return_value = {"models": [{"name": "tinyllama:latest"}]}

        with patch("clipper.ollama_client.requests.get", return_value=first) as get_call:
            with self.assertRaisesRegex(OllamaError, "ollama pull llama3.1:8b"):
                check_ollama("http://127.0.0.1:11434", "llama3.1:8b")
        get_call.assert_called_once_with(
            "http://127.0.0.1:11434/api/tags",
            timeout=5,
        )


if __name__ == "__main__":
    unittest.main()
