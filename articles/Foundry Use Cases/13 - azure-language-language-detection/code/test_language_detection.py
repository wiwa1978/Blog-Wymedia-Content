import unittest
from unittest.mock import patch

import requests

from language_detection import detect_language, language_endpoint, main


class LanguageDetectionTests(unittest.TestCase):
    def test_project_endpoint_uses_resource_origin(self):
        self.assertEqual(
            language_endpoint(
                "https://example.services.ai.azure.com/api/projects/my-project/"
            ),
            "https://example.services.ai.azure.com",
        )

    def test_invalid_project_endpoint_is_rejected(self):
        for value in (
            "",
            "https://example.services.ai.azure.com",
            "https://example.services.ai.azure.com/api/projects",
            "https://example.services.ai.azure.com/api/projects/my-project/extra",
            "https://example.services.ai.azure.com/api/projects/my-project?x=1",
            "http://example.services.ai.azure.com/api/projects/my-project",
        ):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "PROJECT_ENDPOINT"):
                language_endpoint(value)

    @patch("language_detection.detect_language", return_value=("French", "fr", 0.98))
    @patch("language_detection.DefaultAzureCredential")
    @patch("language_detection.load_dotenv")
    @patch("builtins.print")
    @patch.dict(
        "os.environ",
        {
            "PROJECT_ENDPOINT": "https://example.services.ai.azure.com/api/projects/my-project",
            "TEXT": "Bonjour",
        },
    )
    def test_main_uses_project_endpoint(self, print_output, load_dotenv, credential, detect):
        credential.return_value.__enter__.return_value.get_token.return_value.token = "token"
        main()
        detect.assert_called_once_with(
            "https://example.services.ai.azure.com", "token", "Bonjour"
        )
        print_output.assert_called_once_with(
            "Detected language: French (fr), confidence 98%"
        )

    @patch("language_detection.requests.post")
    def test_detects_language(self, post):
        post.return_value.json.return_value = {
            "kind": "LanguageDetectionResults",
            "results": {
                "documents": [
                    {
                        "id": "1",
                        "detectedLanguage": {
                            "name": "French",
                            "iso6391Name": "fr",
                            "confidenceScore": 0.98,
                        },
                    }
                ],
                "errors": [],
            },
        }

        self.assertEqual(
            detect_language("https://example.services.ai.azure.com/", "test-token", "Bonjour"),
            ("French", "fr", 0.98),
        )
        post.assert_called_once_with(
            "https://example.services.ai.azure.com/language/:analyze-text",
            params={"api-version": "2026-05-01"},
            headers={
                "Authorization": "Bearer " + "test-token",
                "Content-Type": "application/json",
            },
            json={
                "kind": "LanguageDetection",
                "parameters": {"modelVersion": "latest"},
                "analysisInput": {"documents": [{"id": "1", "text": "Bonjour"}]},
            },
            timeout=30,
        )

    @patch("language_detection.requests.post")
    def test_document_errors_are_not_success(self, post):
        post.return_value.json.return_value = {
            "results": {"documents": [], "errors": [{"id": "1", "error": {"code": "InvalidDocument"}}]}
        }
        with self.assertRaisesRegex(RuntimeError, "Language detection failed"):
            detect_language("https://example.services.ai.azure.com", "token", "Bonjour")

    @patch("language_detection.requests.post")
    def test_http_error_is_not_parsed(self, post):
        post.return_value.raise_for_status.side_effect = requests.HTTPError("403 Client Error")
        with self.assertRaises(requests.HTTPError):
            detect_language("https://example.services.ai.azure.com", "token", "Bonjour")
        post.return_value.json.assert_not_called()

    @patch("language_detection.requests.post")
    def test_missing_document_is_not_success(self, post):
        post.return_value.json.return_value = {"results": {"documents": [], "errors": []}}
        with self.assertRaisesRegex(ValueError, "did not return document 1"):
            detect_language("https://example.services.ai.azure.com", "token", "Bonjour")


if __name__ == "__main__":
    unittest.main()
