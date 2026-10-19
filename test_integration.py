"""Offline integration tests for real rclone transfers; no Google credentials."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from rclone_backend import copy_command


@unittest.skipUnless(shutil.which("rclone"), "rclone is not installed")
class LocalTransferTests(unittest.TestCase):
    def test_upload_command_against_local_backend(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source"
            destination = base / "destination"
            source.mkdir()
            destination.mkdir()
            (source / "example.txt").write_text("transfer test\n", encoding="utf-8")
            # rclone copy local -> local exercises the same command-line flags
            # without contacting Google or requiring OAuth credentials.
            cmd = copy_command("placeholder", source, "upload")
            cmd[3] = str(destination)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((destination / "example.txt").read_text(encoding="utf-8"), "transfer test\n")

    def test_missing_source_returns_error(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source"
            destination = base / "destination"
            source.mkdir()
            destination.mkdir()
            cmd = copy_command("placeholder", source, "upload")
            cmd[2] = str(base / "missing")
            cmd[3] = str(destination)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(destination.iterdir()), [])

    def test_existing_destination_file_is_updated(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source"
            destination = base / "destination"
            source.mkdir()
            destination.mkdir()
            (source / "same.txt").write_text("new data", encoding="utf-8")
            (destination / "same.txt").write_text("old", encoding="utf-8")
            cmd = copy_command("placeholder", source, "upload")
            cmd[3] = str(destination)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((destination / "same.txt").read_text(encoding="utf-8"), "new data")

    def test_copy_does_not_delete_unrelated_destination_files(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source"
            destination = base / "destination"
            source.mkdir()
            destination.mkdir()
            (source / "new.txt").write_text("new", encoding="utf-8")
            (destination / "keep.txt").write_text("keep", encoding="utf-8")
            cmd = copy_command("placeholder", source, "upload")
            cmd[3] = str(destination)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((destination / "keep.txt").exists())
            self.assertTrue((destination / "new.txt").exists())


if __name__ == "__main__":
    unittest.main()
