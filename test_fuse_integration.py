"""Real rclone/FUSE smoke using isolated local aliases, no Google credentials.

Skips only when the Linux runner lacks a usable /dev/fuse. Read, write, edit
and delete operations happen exclusively in a TemporaryDirectory.
"""
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from mount_drive import command as mount_command


def fuse_usable():
    helper = shutil.which("fusermount3") or shutil.which("fusermount")
    device = Path("/dev/fuse")
    return bool(shutil.which("rclone") and helper and device.exists()
                and os.access(device, os.R_OK | os.W_OK))


def await_condition(check, seconds=32):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            if check():
                return True
        except (OSError, FileNotFoundError):
            pass
        time.sleep(0.2)
    return False


class LocalFuseMountIntegration(unittest.TestCase):
    def _start_mount(self, root, writable):
        remote = root / "source"
        remote.mkdir()
        if not writable:
            (remote / "probe.txt").write_text("fuse-read-ok", encoding="utf-8")
        mount_root = root / "virtual"
        config_file = root / "rclone.conf"
        config_file.write_text(
            "[local_fuse_test]\ntype = alias\nremote = " +
            str(remote) + "\n", encoding="utf-8")
        env = dict(os.environ, RCLONE_CONFIG=str(config_file))
        cmd = mount_command({
            "account": "local_fuse_test", "folder": str(root / "mirror"),
            "mount_read_only": not writable
        }, root=mount_root, create=True)
        mount = mount_root / "local_fuse_test"
        if not writable:
            # Read-only mounts don't need write caching for this smoke.
            cmd = ["rclone", "mount", "local_fuse_test:", str(mount),
                   "--read-only", "--vfs-cache-mode", "off",
                   "--poll-interval", "0", "--dir-cache-time", "5s"]
        process = subprocess.Popen(
            cmd, env=env, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, text=True)
        if not await_condition(mount.is_mount, seconds=18):
            process.terminate()
            try:
                _, errors = process.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                _, errors = process.communicate(timeout=5)
            self.fail("FUSE failed to mount local rclone alias: " + errors[-300:])
        return process, remote, mount

    def _stop_mount(self, process, mount):
        process.terminate()
        try:
            process.wait(timeout=16)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if mount.is_mount():
            subprocess.run(
                [shutil.which("fusermount3") or shutil.which("fusermount"),
                 "-u", str(mount)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
        if process.stderr:
            process.stderr.close()

    @unittest.skipUnless(fuse_usable(), "FUSE helper or /dev/fuse unavailable in CI")
    def test_local_alias_read_only_mount_and_unmount(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            process, remote, mount = self._start_mount(root, writable=False)
            try:
                self.assertTrue(await_condition(
                    lambda: (mount / "probe.txt").exists(), seconds=10))
                self.assertEqual((mount / "probe.txt").read_text(),
                                 "fuse-read-ok")
                with self.assertRaises(OSError):
                    (mount / "not-allowed.txt").write_text("blocked")
            finally:
                self._stop_mount(process, mount)

    @unittest.skipUnless(fuse_usable(), "FUSE helper or /dev/fuse unavailable in CI")
    def test_local_alias_writable_create_modify_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            process, remote, mount = self._start_mount(root, writable=True)
            try:
                new_file = mount / "created-via-fuse.txt"
                new_file.write_text("first", encoding="utf-8")
                self.assertTrue(await_condition(
                    lambda: (remote / "created-via-fuse.txt").exists(),
                    seconds=40), "FUSE failed to upload a newly created file")
                self.assertEqual((remote / "created-via-fuse.txt").read_text(), "first")
                new_file.write_text("second", encoding="utf-8")
                self.assertTrue(await_condition(
                    lambda: (remote / "created-via-fuse.txt").read_text() == "second",
                    seconds=40), "FUSE failed to upload an edited file")
                new_file.unlink()
                self.assertTrue(await_condition(
                    lambda: not (remote / "created-via-fuse.txt").exists(),
                    seconds=20), "FUSE did not propagate deletion on local test remote")
            finally:
                self._stop_mount(process, mount)


if __name__ == "__main__":
    unittest.main()
