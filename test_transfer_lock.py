import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from background_sync import run_once

from transfer_lock import profile_transfer_lock
from background_sync import job_key


class TransferLockTests(unittest.TestCase):
    def test_same_profile_cannot_start_two_transfers(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            local = home / "local"
            local.mkdir()
            state = home / "state"
            with profile_transfer_lock("drive", local, state):
                with self.assertRaisesRegex(RuntimeError, "trabalhando"):
                    with profile_transfer_lock("drive", local, state):
                        pass
            with profile_transfer_lock("drive", local, state):
                self.assertTrue((state / (job_key("drive", local) + ".lock")).exists())

    @patch("background_sync.inventories")
    @patch("background_sync.list_remotes", return_value=["demo"])
    def test_systemd_cycle_recognizes_manual_transfer_lock(self, remotes, inventories):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            folder = base / "local"
            folder.mkdir()
            state = base / "state"
            with profile_transfer_lock("demo", folder, state):
                result = run_once(
                    config={"account": "demo", "folder": str(folder),
                            "auto_sync_enabled": True},
                    state_base=state, backup_base=base / "backups")
                self.assertEqual(result["state"], "busy")
                inventories.assert_not_called()

    def test_two_accounts_can_transfer_independently(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            a = base / "a"
            b = base / "b"
            a.mkdir()
            b.mkdir()
            with profile_transfer_lock("personal", a, base / "state"):
                with profile_transfer_lock("work", b, base / "state"):
                    self.assertEqual(len(list((base / "state").glob("*.lock"))), 2)

    def test_private_state_directory(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            with profile_transfer_lock("drive", base, base / "state"):
                self.assertEqual((base / "state").stat().st_mode & 0o777, 0o700)

    def test_symlink_lock_cannot_overwrite_target(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            local = base / "local"
            local.mkdir()
            state = base / "state"
            state.mkdir()
            victim = base / "important.txt"
            victim.write_text("DO NOT MODIFY", encoding="utf-8")
            lock = state / (job_key("drive", local) + ".lock")
            lock.symlink_to(victim)
            with self.assertRaisesRegex(ValueError, "inseguro"):
                with profile_transfer_lock("drive", local, state):
                    pass
            self.assertEqual(victim.read_text(encoding="utf-8"), "DO NOT MODIFY")

    def test_hardlink_lock_rejected(self):
        import os
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            local = base / "local"
            local.mkdir()
            state = base / "state"
            state.mkdir()
            victim = base / "important.txt"
            victim.write_text("KEEP", encoding="utf-8")
            os.link(victim, state / (job_key("drive", local) + ".lock"))
            with self.assertRaisesRegex(ValueError, "múltiplos links"):
                with profile_transfer_lock("drive", local, state):
                    pass
            self.assertEqual(victim.read_text(encoding="utf-8"), "KEEP")

    def test_symlinked_state_directory_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            local = base / "local"
            local.mkdir()
            state = base / "state"
            real = base / "real-state"
            real.mkdir()
            state.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "simbólico"):
                with profile_transfer_lock("drive", local, state):
                    pass

    def test_lock_permissions_are_private(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            with profile_transfer_lock("drive", base, base / "state"):
                lock = base / "state" / (job_key("drive", base) + ".lock")
                self.assertEqual(lock.stat().st_mode & 0o777, 0o600)

if __name__ == "__main__":
    unittest.main()
