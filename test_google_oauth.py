import unittest
from google_oauth import google_config_command, verify_google_remote
from unittest.mock import patch

class GoogleOAuthTests(unittest.TestCase):
    def test_valid_command(self):
        cmd = google_config_command("meu_drive", "123-abc.apps.googleusercontent.com")
        self.assertEqual(cmd[:5], ["rclone", "config", "create", "meu_drive", "drive"])
        self.assertIn("config_is_local", cmd)
        self.assertIn("true", cmd)
        self.assertNotIn("client_secret", cmd)

    def test_default_client_requires_no_google_cloud_setup(self):
        cmd = google_config_command("pessoal")
        self.assertNotIn("client_id", cmd)
        self.assertEqual(cmd[:5], ["rclone", "config", "create", "pessoal", "drive"])

    @patch("google_oauth.subprocess.run")
    def test_verify_remote_success(self, mock_run):
        mock_run.return_value.returncode = 0
        self.assertTrue(verify_google_remote("conta"))
        self.assertEqual(mock_run.call_args.args[0],
                         ["rclone", "lsd", "conta:"])

    @patch("google_oauth.subprocess.run")
    def test_verify_remote_rejects_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        self.assertFalse(verify_google_remote("conta"))

    def test_verify_remote_bad_name(self):
        with self.assertRaises(ValueError):
            verify_google_remote("../escape")

    def test_invalid_names(self):
        for name in ("", "../evil", "a:b", "a b", "x\n"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                google_config_command(name, "123.apps.googleusercontent.com")

    def test_invalid_client_id(self):
        for client in ("not-google", "--help", "a\n.apps.googleusercontent.com"):
            with self.subTest(client=client), self.assertRaises(ValueError):
                google_config_command("drive", client)

if __name__ == "__main__":
    unittest.main()
