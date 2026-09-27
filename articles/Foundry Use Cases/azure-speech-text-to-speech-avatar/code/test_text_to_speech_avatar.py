import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

import text_to_speech_avatar as avatar


class AvatarSampleTests(unittest.TestCase):
    def test_main_uses_project_endpoint_from_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            here = Path(directory)
            (here / ".env").write_text(
                "PROJECT_ENDPOINT=https://resource.services.ai.azure.com/api/projects/demo\n",
                encoding="utf-8",
            )
            (here / "prompt.txt").write_text("Hello!", encoding="utf-8")
            with (
                patch.object(avatar, "HERE", here),
                patch.dict(
                    avatar.os.environ,
                    {
                        "PROJECT_ENDPOINT": "https://wrong.services.ai.azure.com/api/projects/demo",
                        "AZURE_SPEECH_ENDPOINT": "https://legacy.example.cognitiveservices.azure.com",
                    },
                    clear=True,
                ),
                patch.object(avatar.requests, "Session") as make_session,
                patch.object(avatar, "SpeechTokenAuth") as auth,
                patch.object(avatar, "submit_job", return_value="avatar-id") as submit,
                patch.object(avatar, "wait_for_video", return_value="https://example.test/video.mp4"),
                patch.object(avatar, "download_video"),
            ):
                avatar.main()
                submit.assert_called_once_with(
                    make_session.return_value.__enter__.return_value,
                    "https://resource.cognitiveservices.azure.com",
                    "Hello!",
                )
                self.assertIs(
                    make_session.return_value.__enter__.return_value.auth,
                    auth.return_value,
                )

    def test_entra_token_authenticates_each_request(self):
        with patch.object(avatar, "DefaultAzureCredential") as credential:
            credential.return_value.get_token.side_effect = [
                MagicMock(token="first-token"),
                MagicMock(token="refreshed-token"),
            ]
            auth = avatar.SpeechTokenAuth()
            first = requests.Request(
                "PUT", "https://speech.example.cognitiveservices.azure.com/avatar/batchsyntheses/id"
            ).prepare()
            second = requests.Request(
                "GET", "https://speech.example.cognitiveservices.azure.com/avatar/batchsyntheses/id"
            ).prepare()
            self.assertEqual(auth(first).headers["Authorization"], "Bearer first-token")
            self.assertEqual(auth(second).headers["Authorization"], "Bearer refreshed-token")
            self.assertEqual(
                credential.return_value.get_token.call_args_list,
                [
                    unittest.mock.call(avatar.SPEECH_SCOPE),
                    unittest.mock.call(avatar.SPEECH_SCOPE),
                ],
            )

    def test_foundry_project_url_derives_speech_endpoint(self):
        with patch.dict(
            avatar.os.environ,
            {
                "PROJECT_ENDPOINT": "https://resource.services.ai.azure.com/api/projects/demo/",
                "AZURE_SPEECH_ENDPOINT": "https://unrelated.cognitiveservices.azure.com",
            },
            clear=True,
        ):
            self.assertEqual(
                avatar.speech_endpoint(), "https://resource.cognitiveservices.azure.com"
            )

    def test_direct_speech_resource_url_still_works(self):
        with patch.dict(
            avatar.os.environ,
            {"PROJECT_ENDPOINT": "https://other.cognitiveservices.azure.com/"},
            clear=True,
        ):
            self.assertEqual(
                avatar.speech_endpoint(), "https://other.cognitiveservices.azure.com"
            )

    def test_unrelated_or_malformed_endpoints_are_rejected(self):
        for endpoint in (
            "https://resource.services.ai.azure.com/openai/v1",
            "https://resource.services.ai.azure.com/api/projects/demo/other",
            "https://resource.services.ai.azure.com.evil.example/api/projects/demo",
            "https://user:password@resource.services.ai.azure.com/api/projects/demo",
            "http://resource.services.ai.azure.com/api/projects/demo",
        ):
            with self.subTest(endpoint=endpoint), patch.dict(
                avatar.os.environ, {"PROJECT_ENDPOINT": endpoint}, clear=True
            ):
                with self.assertRaises(ValueError):
                    avatar.speech_endpoint()

    def test_missing_env_file_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(avatar, "HERE", Path(directory)), patch.dict(
                avatar.os.environ, {}, clear=True
            ):
                with self.assertRaisesRegex(FileNotFoundError, ".env.example"):
                    avatar.main()

    def test_submit_job_builds_standalone_speech_request(self):
        session = MagicMock()
        with patch.object(avatar.uuid, "uuid4") as make_id:
            make_id.return_value.hex = "123abc"
            with patch.dict(avatar.os.environ, {}, clear=True):
                job_id = avatar.submit_job(
                    session, "https://speech.example.cognitiveservices.azure.com", "Hello!"
                )

        self.assertEqual(job_id, "avatar-123abc")
        args, kwargs = session.put.call_args
        self.assertEqual(
            args[0],
            "https://speech.example.cognitiveservices.azure.com"
            "/avatar/batchsyntheses/avatar-123abc?api-version=2024-08-01",
        )
        self.assertEqual(kwargs["json"]["inputKind"], "PlainText")
        self.assertEqual(kwargs["json"]["inputs"], [{"content": "Hello!"}])
        self.assertEqual(
            kwargs["json"]["avatarConfig"]["talkingAvatarStyle"], "graceful-sitting"
        )
        self.assertEqual(
            kwargs["json"]["synthesisConfig"]["voice"], "en-US-AvaMultilingualNeural"
        )

    def test_polling_returns_signed_video_url(self):
        session = MagicMock()
        session.get.return_value.json.side_effect = [
            {"status": "Running"},
            {"status": "Succeeded", "outputs": {"result": "https://example.test/video.mp4?sig=x"}},
        ]
        with patch.object(avatar.time, "sleep"):
            url = avatar.wait_for_video(session, "https://speech.example.test", "avatar-id")
        self.assertEqual(url, "https://example.test/video.mp4?sig=x")
        self.assertEqual(session.get.call_count, 2)

    def test_failed_job_reports_error(self):
        session = MagicMock()
        session.get.return_value.json.return_value = {
            "status": "Failed",
            "properties": {"error": {"message": "Invalid voice"}},
        }
        with self.assertRaisesRegex(RuntimeError, "Invalid voice"):
            avatar.wait_for_video(session, "https://speech.example.test", "avatar-id")

    def test_download_does_not_send_speech_key_and_cleans_partial_file(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.iter_content.return_value = [b"video", b" bytes"]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "avatar.mp4"
            with patch.object(avatar.requests, "get", return_value=response) as get:
                avatar.download_video("https://example.test/video.mp4?sig=x", destination)
            self.assertEqual(destination.read_bytes(), b"video bytes")
            self.assertFalse(destination.with_suffix(".mp4.part").exists())
            self.assertNotIn("headers", get.call_args.kwargs)

            response.iter_content.side_effect = requests.ConnectionError("Interrupted")
            with patch.object(avatar.requests, "get", return_value=response):
                with self.assertRaises(requests.ConnectionError):
                    avatar.download_video("https://example.test/video.mp4?sig=x", destination)
            self.assertFalse(destination.with_suffix(".mp4.part").exists())
            self.assertEqual(destination.read_bytes(), b"video bytes")


if __name__ == "__main__":
    unittest.main()
