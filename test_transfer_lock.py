import tempfile
import unittest
from pathlib import Path

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

if __name__ == "__main__":
    unittest.main()
