"""QA of systemd exit codes for real synchronization outcomes."""
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import background_sync


class ServiceExitTests(unittest.TestCase):
    def run_status(self, state):
        fake = {"state": state, "copied": 0, "profiles": []}
        with (patch("background_sync.run_profiles", return_value=fake),
              patch("background_sync.notify_if_changed"),
              patch("background_sync.read_json", return_value={}),
              patch("sys.argv", ["background_sync.py", "--once"]),
              redirect_stdout(io.StringIO()) as printed):
            exit_code = background_sync.main()
        self.assertIn('"state": "' + state + '"', printed.getvalue())
        return exit_code

    def test_google_quota_returns_failed_systemd_exit(self):
        self.assertEqual(self.run_status("quota"), 1)

    def test_network_or_oauth_failure_returns_failed_exit(self):
        self.assertEqual(self.run_status("error"), 1)

    def test_pending_batch_is_recoverable_not_failure(self):
        self.assertEqual(self.run_status("partial"), 0)

    def test_conflicts_are_not_silently_deleted_or_service_failure(self):
        self.assertEqual(self.run_status("conflicts"), 0)

    def test_completed_sync_returns_success(self):
        self.assertEqual(self.run_status("ok"), 0)


if __name__ == "__main__":
    unittest.main()
