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
                self.assertEqual(settings.load_settings(), {"folder": "/tmp/drive", "account": "conta", "auto_sync_enabled": False, "mount_read_only": True, "auto_archive_deletions": False})
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

    def test_persistent_background_sync_opt_in(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "config"
            with patch.object(settings, "CONFIG_DIR", directory), patch.object(
                    settings, "CONFIG_FILE", directory / "settings.json"):
                settings.save_settings("/tmp/folder", "cloud",
                                       auto_sync_enabled=True)
                self.assertIs(settings.load_settings()["auto_sync_enabled"], True)
                self.assertEqual(os.stat(settings.CONFIG_FILE).st_mode & 0o777, 0o600)

    def test_archive_is_opt_in_and_persists(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "config"
            with patch.object(settings, "CONFIG_DIR", directory), patch.object(
                    settings, "CONFIG_FILE", directory / "settings.json"):
                settings.save_settings("/tmp/drive", "pessoal")
                self.assertIs(settings.load_settings()["auto_archive_deletions"], False)
                settings.save_settings("/tmp/drive", "pessoal", auto_archive_deletions=True)
                self.assertIs(settings.load_settings()["auto_archive_deletions"], True)

    def test_mount_read_only_preference(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "config"
            with patch.object(settings, "CONFIG_DIR", directory), patch.object(
                    settings, "CONFIG_FILE", directory / "settings.json"):
                settings.save_settings("/tmp/drive", "pessoal", mount_read_only=False)
                self.assertIs(settings.load_settings()["mount_read_only"], False)
                settings.save_settings("/tmp/drive", "pessoal")
                self.assertIs(settings.load_settings()["mount_read_only"], True)

    def test_corrupt_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "settings.json"
            file.write_text("{invalid", encoding="utf-8")
            with patch.object(settings, "CONFIG_FILE", file):
                self.assertEqual(settings.load_settings(), {})

if __name__ == "__main__":
    unittest.main()
