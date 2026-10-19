import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from safe_sync import copyto_command, execute_additions
from sync_plan import SyncPlan

class SafeSyncTests(unittest.TestCase):
    def test_commands_are_non_destructive(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "new.txt").write_text("data")
            cmd = copyto_command("drive", root, "new.txt", "upload")
            self.assertEqual(cmd[1], "copyto")
            self.assertIn("--ignore-existing", cmd)
            self.assertNotIn("sync", cmd)

    def test_rejects_local_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "exists").write_text("keep")
            with self.assertRaises(ValueError):
                copyto_command("drive", root, "exists", "download")

    def test_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "link").symlink_to("/etc/passwd")
            with self.assertRaises(ValueError):
                copyto_command("drive", root, "link", "upload")

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                copyto_command("drive", root, "../escape", "download")

    @patch("safe_sync.remote_inventory")
    @patch("safe_sync.local_inventory")
    def test_dry_run_never_copies(self, local, remote):
        with tempfile.TemporaryDirectory() as root:
            local.return_value = {}
            remote.return_value = {"remote.txt": ("md5", "abc")}
            plan, count = execute_additions("drive", root, dry_run=True)
            self.assertEqual(plan.download, ("remote.txt",))
            self.assertEqual(count, 0)

    @patch("safe_sync.remote_inventory")
    @patch("safe_sync.local_inventory")
    def test_large_batch_refused(self, local, remote):
        with tempfile.TemporaryDirectory() as root:
            local.return_value = {}
            remote.return_value = {str(i): ("md5", "x") for i in range(101)}
            with self.assertRaises(ValueError):
                execute_additions("drive", root, dry_run=False)

if __name__ == "__main__":
    unittest.main()
