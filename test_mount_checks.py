"""Reproduce Zorin mount configuration errors without network or OAuth tokens."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mount_checks import inspect_mount, format_mount_report
from mount_drive import validate_mount
from mount_health import classify_mount_error


class MountPreflightTests(unittest.TestCase):
    @patch("mount_checks._command_ready", return_value=True)
    @patch("mount_checks.list_remotes", return_value=["meu_drive"])
    @patch("mount_checks.shutil.which", side_effect=lambda name: "/usr/bin/" + name)
    def test_local_remote_and_safe_folder(self, which, remotes, ready):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mirror = root / "espelho"
            mirror.mkdir()
            result = inspect_mount(
                {"account": "meu_drive", "folder": str(mirror)},
                root=root / "DriveOnline")
            checks = {item["name"]: item for item in result["checks"]}
            self.assertTrue(checks["Conta disponível ao rclone"]["ok"])
            self.assertTrue(checks["Diretório do disco virtual"]["ok"])
            self.assertEqual(remotes.call_count, 1)

    @patch("mount_checks._command_ready", return_value=True)
    @patch("mount_checks.list_remotes", return_value=[])
    @patch("mount_checks.shutil.which", side_effect=lambda name: "/usr/bin/" + name)
    def test_missing_remote_is_diagnosed_without_cloud_access(self, which, remotes, ready):
        with tempfile.TemporaryDirectory() as tmp:
            result = inspect_mount({
                "account": "meu_drive", "folder": str(Path(tmp) / "mirror")},
                root=Path(tmp) / "online")
        details = format_mount_report(result)
        self.assertFalse(result["ready"])
        self.assertIn("Conta ausente", details)
        self.assertIn("403", details)
        # Only rclone 'help mount', a local 'listremotes' and systemctl probes.
        self.assertTrue(all(call.args[0][0] != "lsd" for call in ready.call_args_list))

    @patch("mount_checks._command_ready", return_value=False)
    @patch("mount_checks.shutil.which", return_value=None)
    def test_missing_fuse_and_rclone_reports_install_steps(self, which, ready):
        result = inspect_mount({"account": None})
        text = format_mount_report(result)
        self.assertIn("Instale o rclone", text)
        self.assertIn("Instale fuse3", text)

    @patch("mount_drive.os.getuid", return_value=-1)
    def test_root_owned_empty_mount_folder_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            online = Path(tmp) / "virtual"
            (online / "demo").mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "outro usuário"):
                validate_mount(
                    {"account": "demo", "folder": str(Path(tmp) / "mirror")},
                    root=online, require_tools=False)

    @patch("mount_drive.os.access", return_value=False)
    def test_unwritable_mount_folder_rejected(self, access):
        with tempfile.TemporaryDirectory() as tmp:
            online = Path(tmp) / "virtual"
            (online / "demo").mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "permissão"):
                validate_mount(
                    {"account": "demo", "folder": str(Path(tmp) / "mirror")},
                    root=online, require_tools=False)

    def test_mount_error_classification_no_raw_oauth_info(self):
        raw = "Conta ausente no rclone deste serviço. token=do-not-share"
        text = classify_mount_error(raw)
        self.assertIn("rclone.conf", text)
        self.assertNotIn("do-not-share", text)


if __name__ == "__main__":
    unittest.main()
