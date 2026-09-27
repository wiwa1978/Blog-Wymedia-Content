import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from context_extractor import analyze_image, resource_endpoint


PROJECT_ENDPOINT = "https://example.services.ai.azure.com/api/projects/demo"
ENDPOINT = "https://example.services.ai.azure.com"


class ContentExtractorTests(unittest.TestCase):
    def test_derives_resource_endpoint_from_project_endpoint(self):
        self.assertEqual(resource_endpoint(PROJECT_ENDPOINT), ENDPOINT)
        self.assertEqual(resource_endpoint(PROJECT_ENDPOINT + "/"), ENDPOINT)

    def test_rejects_non_project_endpoints(self):
        for value in (
            ENDPOINT,
            PROJECT_ENDPOINT + "/extra",
            PROJECT_ENDPOINT + "?api-version=2026-06-01-preview",
            "http://example.services.ai.azure.com/api/projects/demo",
            "https://<resource>.services.ai.azure.com/api/projects/<project>",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resource_endpoint(value)

    @patch("context_extractor.ContentUnderstandingClient")
    def test_image_search_returns_untruncated_result(self, client_class):
        credential = MagicMock()
        result_data = {
            "analyzerId": "prebuilt-imageSearch",
            "contents": [{"markdown": "A landscape", "fields": {"Summary": {"valueString": "A landscape"}}}],
            "warnings": [],
        }
        client = client_class.return_value.__enter__.return_value
        client.begin_analyze_binary.return_value.result.return_value.as_dict.return_value = result_data
        with tempfile.TemporaryDirectory() as directory:
            for suffix, mime_type in ((".png", "image/png"), (".jpg", "image/jpeg")):
                with self.subTest(suffix=suffix):
                    image = Path(directory) / f"input{suffix}"
                    image.write_bytes(b"test-image")
                    self.assertEqual(analyze_image(image, ENDPOINT, credential), result_data)
                    client.begin_analyze_binary.assert_called_with(
                        analyzer_id="prebuilt-imageSearch",
                        binary_input=b"test-image",
                        content_type=mime_type,
                    )
        client_class.assert_called_with(
            endpoint=ENDPOINT, credential=credential, api_version="2026-06-01-preview"
        )


if __name__ == "__main__":
    unittest.main()
