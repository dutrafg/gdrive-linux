import unittest
from google_oauth import google_config_command

class GoogleOAuthTests(unittest.TestCase):
    def test_valid_command(self):
        cmd = google_config_command("meu_drive", "123-abc.apps.googleusercontent.com")
        self.assertEqual(cmd[:5], ["rclone", "config", "create", "meu_drive", "drive"])
        self.assertIn("config_is_local", cmd)
        self.assertIn("true", cmd)
        self.assertNotIn("client_secret", cmd)

    def test_invalid_names(self):
        for name in ("", "../evil", "a:b", "a b", "x\n"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                google_config_command(name, "123.apps.googleusercontent.com")

    def test_invalid_client_id(self):
        for client in ("", "not-google", "--help", "a\n.apps.googleusercontent.com"):
            with self.subTest(client=client), self.assertRaises(ValueError):
                google_config_command("drive", client)

if __name__ == "__main__":
    unittest.main()
