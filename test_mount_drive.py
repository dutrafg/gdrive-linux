"""Unit tests for mount safety; no FUSE device or account needed."""
import tempfile
import unittest
from pathlib import Path

from mount_drive import command, mount_path, validate_mount

class MountTests(unittest.TestCase):
    def test_read_only_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            mirror = Path(tmp) / "mirror"
            mirror.mkdir()
            config = {"account": "pessoal", "folder": str(mirror)}
            cmd = command(config, root=Path(tmp)/"virtual")
            self.assertEqual(cmd[:3], ["rclone", "mount", "pessoal:"])
            self.assertIn("--read-only", cmd)
            self.assertIn("--vfs-cache-mode", cmd)
            self.assertIn("writes", cmd)

    def test_write_mode_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {"account": "personal", "folder": str(Path(tmp)/"mirror"),
                      "mount_read_only": False}
            self.assertNotIn("--read-only", command(config, root=Path(tmp)/"virtual"))

    def test_rejects_nested_mirror_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "DriveOnline"
            with self.assertRaises(ValueError):
                validate_mount({"account": "personal",
                                "folder": str(root/"personal"/"mirror")},
                               root=root, require_tools=False)

    def test_rejects_non_empty_mount(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"mounts"
            mount = mount_path("personal", root)
            mount.mkdir(parents=True)
            (mount/"keep.txt").write_text("important", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_mount({"account": "personal",
                                "folder": str(Path(tmp)/"mirror")},
                               root=root, require_tools=False)

    def test_rejects_remote_path_escape(self):
        with self.assertRaises(ValueError):
            mount_path("../escape")
        with self.assertRaises(ValueError):
            mount_path("bad remote")

    def test_no_unexpected_directories_without_activation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"mounts"
            validate_mount({"account": "personal",
                            "folder": str(Path(tmp)/"mirror")},
                           root=root, require_tools=False)
            self.assertFalse(root.exists())

if __name__ == "__main__":
    unittest.main()
