import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from translate_text import load_input_text, main, translate, translator_endpoint_from_project


class TranslateTextTests(unittest.TestCase):
    def test_load_input_text_reads_utf8_and_multiline(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.txt"
            path.write_text("  Bonjour\n世界  \n", encoding="utf-8")
            self.assertEqual(load_input_text(path), "Bonjour\n世界")

            path.write_text(" \n\t", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Add text to input.txt"):
                load_input_text(path)

            path.unlink()
            with self.assertRaises(FileNotFoundError):
                load_input_text(path)

    def test_project_endpoint_derives_translator_resource(self):
        self.assertEqual(
            translator_endpoint_from_project(
                "https://example.services.ai.azure.com/api/projects/my-project/"
            ),
            "https://example.cognitiveservices.azure.com",
        )

    def test_invalid_project_endpoints_fail(self):
        for endpoint in (
            "",
            "https://example.cognitiveservices.azure.com",
            "http://example.services.ai.azure.com/api/projects/my-project",
            "https://example.services.ai.azure.com/api/projects/",
            "https://example.services.ai.azure.com/api/projects/p/other",
            "https://example.services.ai.azure.com/api/projects/p?x=1",
            "https://example.services.ai.azure.com:443/api/projects/p",
            "https://example.services.ai.azure.com.evil.test/api/projects/p",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaisesRegex(
                ValueError, "PROJECT_ENDPOINT"
            ):
                translator_endpoint_from_project(endpoint)

    @patch("translate_text.requests.post")
    @patch("translate_text.DefaultAzureCredential")
    @patch("translate_text.load_dotenv")
    @patch("translate_text.Path.read_text", return_value="Good morning\nworld")
    def test_main_uses_project_endpoint_and_input_file(
        self, read_text, _load_dotenv, credential, post
    ):
        credential.return_value.__enter__.return_value.get_token.return_value.token = "token"
        post.return_value.json.return_value = {
            "value": [{"translations": [{"language": "fr", "text": "Bonjour"}]}]
        }
        config = {
            "PROJECT_ENDPOINT": "https://example.services.ai.azure.com/api/projects/p",
            "TRANSLATOR_ENDPOINT": "https://wrong.cognitiveservices.azure.com",
            "TEXT": "ignored legacy text",
            "TARGET_LANGUAGES": "fr",
            "SOURCE_LANGUAGE": "en",
        }
        with patch.dict(os.environ, config):
            with patch("builtins.print"):
                main()
        self.assertEqual(
            post.call_args.args[0],
            "https://example.cognitiveservices.azure.com/translator/text/translate",
        )
        self.assertEqual(
            post.call_args.kwargs["json"]["inputs"][0]["text"],
            "Good morning\nworld",
        )
        read_text.assert_called_once_with(encoding="utf-8")

    @patch("translate_text.requests.post")
    def test_auto_detect_and_multiple_targets(self, post):
        post.return_value.json.return_value = {
            "value": [
                {
                    "detectedLanguage": {"language": "en", "score": 1.0},
                    "translations": [
                        {"language": "fr", "text": "Bonjour"},
                        {"language": "de", "text": "Hallo"},
                    ],
                }
            ]
        }

        detected, translations = translate(
            "https://example.cognitiveservices.azure.com/",
            "test-token",
            "Hello",
            ["fr", "de"],
        )

        self.assertEqual(detected, "en")
        self.assertEqual(translations, [("fr", "Bonjour"), ("de", "Hallo")])
        post.assert_called_once_with(
            "https://example.cognitiveservices.azure.com/translator/text/translate",
            params={"api-version": "2026-06-06"},
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json",
            },
            json={
                "inputs": [
                    {
                        "text": "Hello",
                        "targets": [{"language": "fr"}, {"language": "de"}],
                    }
                ]
            },
            timeout=30,
        )

    @patch("translate_text.requests.post")
    def test_explicit_source_and_unexpected_response(self, post):
        post.return_value.json.return_value = {
            "value": [{"translations": [{"language": "fr", "text": "Bonjour"}]}]
        }
        self.assertEqual(
            translate("https://example.cognitiveservices.azure.com", "token", "Hello", ["fr"], "en"),
            (None, [("fr", "Bonjour")]),
        )
        self.assertEqual(
            post.call_args.kwargs["json"]["inputs"][0]["language"], "en"
        )

        post.return_value.json.return_value = {"value": []}
        with self.assertRaisesRegex(ValueError, "Unexpected Translator response shape"):
            translate("https://example.cognitiveservices.azure.com", "token", "Hello", ["fr"])

    @patch("translate_text.requests.post")
    def test_http_failure_is_not_parsed_as_success(self, post):
        post.return_value.raise_for_status.side_effect = requests.HTTPError(
            "403 Client Error"
        )
        with self.assertRaises(requests.HTTPError):
            translate("https://example.cognitiveservices.azure.com", "token", "Hello", ["fr"])
        post.return_value.json.assert_not_called()


if __name__ == "__main__":
    unittest.main()
