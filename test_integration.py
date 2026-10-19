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



    def test_automatic_download_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source, destination = base / "cloud", base / "local"
            source.mkdir()
            destination.mkdir()
            (source / "same.txt").write_text("cloud", encoding="utf-8")
            (destination / "same.txt").write_text("local edits", encoding="utf-8")
            (source / "new.txt").write_text("new from cloud", encoding="utf-8")
            cmd = copy_command("placeholder", destination, "download", skip_existing=True)
            cmd[2] = str(source)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((destination / "same.txt").read_text(encoding="utf-8"), "local edits")
            self.assertEqual((destination / "new.txt").read_text(encoding="utf-8"), "new from cloud")


    def test_safe_copyto_never_overwrites_existing_destination(self):
        from safe_sync import copyto_command
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source, dest = base / "local", base / "cloud"
            source.mkdir()
            dest.mkdir()
            (source / "shared.txt").write_text("local", encoding="utf-8")
            (dest / "shared.txt").write_text("remote", encoding="utf-8")
            (source / "new.txt").write_text("new", encoding="utf-8")
            for name in ("shared.txt", "new.txt"):
                cmd = copyto_command("drive", source, name, "upload")
                cmd[3] = str(dest / name)
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((dest / "shared.txt").read_text(encoding="utf-8"), "remote")
            self.assertEqual((dest / "new.txt").read_text(encoding="utf-8"), "new")

if __name__ == "__main__":
    unittest.main()
