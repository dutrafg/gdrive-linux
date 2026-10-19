import unittest
from datetime import datetime, timedelta, timezone
from rclone_errors import friendly, is_rate_limit, cooldown_active, quota_retry_after, rclone_limits

class RcloneErrorTests(unittest.TestCase):
    def test_google_user_query_limit(self):
        sample = 'Error 403: Quota exceeded for quota metric Queries and limit userQueriesPerMinutePerProject: RATE_LIMIT_EXCEEDED'
        self.assertTrue(is_rate_limit(sample))
        self.assertIn("Client ID", friendly(sample))

    def test_unrelated_error_not_quota(self):
        self.assertFalse(is_rate_limit("file not found"))
        self.assertIn("sem permissão", friendly("Permission denied").lower())

    def test_cooldown_time(self):
        now = datetime(2026, 10, 19, 19, 0, tzinfo=timezone.utc)
        later = quota_retry_after(now)
        self.assertTrue(cooldown_active({"state":"quota","retry_after":later}, now))
        self.assertFalse(cooldown_active({"state":"quota","retry_after":later},
                                         now + timedelta(minutes=30)))
        self.assertFalse(cooldown_active({"state":"ok","retry_after":later}, now))

    def test_rclone_limits_are_valid_argument_pairs(self):
        self.assertEqual(rclone_limits(), ["--tpslimit", "2", "--tpslimit-burst", "2"])

if __name__ == "__main__":
    unittest.main()
