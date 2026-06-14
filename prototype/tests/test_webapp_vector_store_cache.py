import unittest
from unittest.mock import patch

from apps.core import version_runner


class WebappVectorStoreCacheTests(unittest.TestCase):
    @patch("apps.core.version_runner.get_vector_store_cached")
    @patch("apps.core.version_runner.knowledge_base_fingerprint", return_value=123.0)
    @patch("apps.core.version_runner.knowledge_base_path_for_version")
    @patch("apps.core.version_runner.get_config_cached", return_value={})
    @patch("apps.core.version_runner.path_mtime", return_value=1.0)
    @patch("apps.core.version_runner.municipality_config_path_for_version")
    @patch("apps.core.version_runner.active_model_metadata")
    def test_vector_store_cache_key_includes_retrieval_embedding_profile(
            self,
            mock_active_model_metadata,
            _mock_config_path,
            _mock_path_mtime,
            _mock_get_config,
            mock_knowledge_base_path,
            _mock_fingerprint,
            mock_get_vector_store,
    ):
        mock_active_model_metadata.return_value = {
            "retrieval_embedding_provider": "openai",
            "retrieval_embedding_model": "text-embedding-3-small",
        }
        mock_knowledge_base_path.return_value = "kb-path"

        version_runner.pipeline_kwargs_for("V5", "Testanfrage")

        mock_get_vector_store.assert_called_once_with(
            "V5",
            "kb-path",
            123.0,
            "openai",
            "text-embedding-3-small",
        )


if __name__ == "__main__":
    unittest.main()
