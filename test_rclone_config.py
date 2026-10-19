import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rclone_config import (
    activate_worker_config, normalize_config_path, selected_config_path)


class RcloneConfigurationTests(unittest.TestCase):
    def test_worker_reads_saved_config_path(self):
        with tempfile.TemporaryDirectory() as root:
            conf = Path(root) / "rclone.conf"
            conf.write_text("[demo]\ntype=alias\nremote=/tmp\n", encoding="utf-8")
            environment = {}
            chosen = activate_worker_config({"rclone_config_file": str(conf)}, environment)
            self.assertEqual(chosen, str(conf))
            self.assertEqual(environment["RCLONE_CONFIG"], str(conf))

    def test_user_configuration_precedes_inherited_environment(self):
        with tempfile.TemporaryDirectory() as root:
            saved = Path(root) / "saved.conf"
            inherited = Path(root) / "inherited.conf"
            saved.write_text("saved", encoding="utf-8")
            inherited.write_text("inherited", encoding="utf-8")
            chosen = selected_config_path({"rclone_config_file": str(saved)},
                                          {"RCLONE_CONFIG": str(inherited)})
            self.assertEqual(chosen, str(saved))

    def test_malformed_or_missing_config_is_rejected(self):
        for value in ("missing\npath", "/a/file/that/does/not/exist.conf"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_config_path(value)

    def test_missing_saved_config_does_not_use_other_account(self):
        with self.assertRaises(ValueError):
            activate_worker_config({"rclone_config_file": "/tmp/missing-saved.conf"},
                                   {"RCLONE_CONFIG": "/tmp/other-rclone.conf"})

    def test_blank_setting_can_use_inherited_config(self):
        with tempfile.TemporaryDirectory() as root:
            conf = Path(root) / "rclone.conf"
            conf.write_text("[demo]", encoding="utf-8")
            self.assertEqual(
                selected_config_path({"rclone_config_file": ""},
                                     {"RCLONE_CONFIG": str(conf)}), str(conf))

if __name__ == "__main__":
    unittest.main()
