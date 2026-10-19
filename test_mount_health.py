"""Mount readiness/diagnostic regression coverage without Google credentials/FUSE."""
import unittest
from pathlib import Path
from unittest.mock import patch

from mount_health import (classify_mount_error, mount_diagnosis,
                          service_state, mount_ready)

class MountHealthTests(unittest.TestCase):
    def test_quota_403_is_actionable_and_does_not_echo_json(self):
        details = ('{"reason":"RATE_LIMIT_EXCEEDED",'
                   '"quota_metric":"drive.googleapis.com/default",'
                   '"token":"secret-sensitive"}')
        result = classify_mount_error(details)
        self.assertIn("403", result)
        self.assertIn("Client ID", result)
        self.assertNotIn("secret-sensitive", result)

    def test_fusermount_permission_error(self):
        log = "fusermount3: mount failed: Permission denied"
        self.assertIn("FUSE", classify_mount_error(log))

    def test_unknown_flag_old_rclone(self):
        self.assertIn("Atualize o rclone", classify_mount_error(
            "Fatal error: flag provided but not defined: -vfs-cache-max-size"))

    def test_bad_auth_requires_reconnect(self):
        self.assertIn("Reautorize", classify_mount_error(
            "Error 401 invalid_grant"))

    @patch("mount_health.mount_ready", return_value=False)
    def test_service_active_not_equal_mounted(self, mounted):
        result = mount_diagnosis("/tmp/example", state="active",
                                 journal="RATE_LIMIT_EXCEEDED some secret")
        self.assertIn("NÃO está montado", result)
        self.assertNotIn("some secret", result)

    @patch("mount_health.mount_ready", return_value=False)
    def test_service_is_starting(self, mounted):
        self.assertIn("iniciando", mount_diagnosis(
            "/tmp/example", state="activating"))

    @patch("mount_health.mount_ready", return_value=True)
    def test_real_fuse_mount_is_ready(self, mounted):
        self.assertIn("montado", mount_diagnosis(
            "/tmp/example", state="inactive"))

    @patch("mount_health.command_output", return_value=(0, "failed\n", ""))
    def test_systemd_failed_status(self, command_output):
        self.assertEqual(service_state(), "failed")

    @patch("mount_health.command_output", return_value=(1, "", ""))
    def test_systemd_unavailable(self, command_output):
        self.assertEqual(service_state(), "unknown")

if __name__ == "__main__":
    unittest.main()
