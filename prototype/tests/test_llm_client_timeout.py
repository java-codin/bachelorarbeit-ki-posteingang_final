import os
import unittest
from unittest.mock import patch

from src.core import llm_client


class LlmClientTimeoutTests(unittest.TestCase):
    @patch.dict(os.environ, {"OLLAMA_REQUEST_TIMEOUT_SECONDS": "3.5"})
    @patch("ollama.Client")
    def test_ollama_json_call_uses_configured_timeout(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client.chat.return_value = {
            "message": {
                "content": '{"ok": true}'
            }
        }

        result = llm_client._chat_json_ollama(
            messages=[{"role": "user", "content": "Test"}],
            model="llama3.1",
            temperature=0,
        )

        self.assertEqual(result, {"ok": True})
        mock_client_class.assert_called_once_with(timeout=3.5)

    @patch.dict(os.environ, {"OLLAMA_REQUEST_TIMEOUT_SECONDS": "0"})
    def test_ollama_timeout_must_be_positive(self):
        with self.assertRaises(ValueError):
            llm_client._get_ollama_timeout_seconds()


if __name__ == "__main__":
    unittest.main()
