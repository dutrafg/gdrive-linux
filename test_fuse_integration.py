"""Optional local FUSE integration test; skips when CI kernel does not expose FUSE.

Uses an isolated rclone alias to a temporary local folder. Does not use Google
credentials, network or any of the user's personal files.
"""
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


def fuse_usable():
    helper = shutil.which("fusermount3") or shutil.which("fusermount")
    device = Path("/dev/fuse")
    return bool(shutil.which("rclone") and helper and device.exists()
                and os.access(device, os.R_OK | os.W_OK))


class LocalFuseMountIntegration(unittest.TestCase):
    @unittest.skipUnless(fuse_usable(), "FUSE helper or /dev/fuse unavailable in CI")
    def test_actual_local_alias_mount_and_unmount(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / "source"
            mount = root / "mount"
            remote.mkdir()
            mount.mkdir()
            (remote / "fuse-probe.txt").write_text("rclone-fuse-ok", encoding="utf-8")
            config = root / "rclone.conf"
            config.write_text("[local_fuse_test]\ntype = alias\nremote = " +
                              str(remote) + "\n", encoding="utf-8")
            env = dict(os.environ, RCLONE_CONFIG=str(config))
            command = ["rclone", "mount", "local_fuse_test:", str(mount),
                       "--read-only", "--vfs-cache-mode", "off",
                       "--poll-interval", "0", "--dir-cache-time", "5s"]
            process = subprocess.Popen(
                command, env=env, stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 18
                while time.monotonic() < deadline:
                    if mount.is_mount():
                        break
                    if process.poll() is not None:
                        _, errors = process.communicate(timeout=2)
                        self.fail("rclone mount exited unexpectedly: " +
                                  errors[-300:])
                    time.sleep(0.3)
                self.assertTrue(mount.is_mount(), "FUSE did not mount within 18s")
                self.assertEqual((mount / "fuse-probe.txt").read_text(encoding="utf-8"),
                                 "rclone-fuse-ok")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                if mount.is_mount():
                    subprocess.run(
                        [shutil.which("fusermount3") or shutil.which("fusermount"),
                         "-u", str(mount)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)


if __name__ == "__main__":
    unittest.main()
