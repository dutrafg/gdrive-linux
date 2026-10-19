import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import settings

class SettingsTests(unittest.TestCase):
    def test_roundtrip_and_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "config"
            with patch.object(settings, "CONFIG_DIR", directory), patch.object(settings, "CONFIG_FILE", directory / "settings.json"):
                settings.save_settings("/tmp/drive", "conta")
                self.assertEqual(settings.load_settings(), {"folder": "/tmp/drive", "account": "conta"})
                self.assertEqual(os.stat(settings.CONFIG_FILE).st_mode & 0o777, 0o600)
                self.assertEqual(os.stat(directory).st_mode & 0o777, 0o700)

    def test_account_display_names_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "config"
            with patch.object(settings, "CONFIG_DIR", directory), patch.object(
                    settings, "CONFIG_FILE", directory / "settings.json"):
                settings.save_settings("/tmp/drive", "pessoal",
                                       {"pessoal": "Uso pessoal", "trabalho": "Trabalho"})
                restored = settings.load_settings()
                self.assertEqual(restored["account_names"]["pessoal"], "Uso pessoal")
                self.assertEqual(restored["account_names"]["trabalho"], "Trabalho")
                self.assertEqual(os.stat(settings.CONFIG_FILE).st_mode & 0o777, 0o600)

    def test_corrupt_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "settings.json"
            file.write_text("{invalid", encoding="utf-8")
            with patch.object(settings, "CONFIG_FILE", file):
                self.assertEqual(settings.load_settings(), {})

if __name__ == "__main__":
    unittest.main()
