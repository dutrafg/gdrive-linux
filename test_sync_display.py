import unittest
from datetime import datetime, timedelta, timezone

from sync_display import profile_lines, last_activity_age, nonnegative_count


class SyncDisplayTests(unittest.TestCase):
    def test_per_account_status_contains_progress_but_not_paths(self):
        data = {"profiles": [
            {"account": "pessoal", "mode": "upload", "state": "partial",
             "copied": 3, "pending": 9, "folder": "/home/user/secret"},
            {"account": "trabalho", "mode": "download", "state": "quota",
             "copied": 0, "pending": 0}]}
        message = "\n".join(profile_lines(data))
        self.assertIn("pessoal", message)
        self.assertIn("9 pendente(s)", message)
        self.assertIn("temporariamente limitada", message)
        self.assertNotIn("/home/user/secret", message)

    def test_status_is_bounded_and_safe_for_bad_local_data(self):
        values = [{"account": "unsafe\npath/../../", "copied": "invalid"},
                  {"account": "test", "pending": -1},
                  {"account": "third"},
                  {"account": "fourth"},
                  {"account": "fifth"}]
        lines = profile_lines({"profiles": values}, max_profiles=3)
        self.assertEqual(len(lines), 4)
        self.assertNotIn("\npath", lines[0])
        self.assertEqual(nonnegative_count("invalid"), 0)

    def test_interrupted_sync_reports_unverified_without_paths(self):
        result = profile_lines({"profiles": [
            {"account": "pessoal", "state": "error", "copied": 0,
             "pending": 3, "unverified_transfers": 2,
             "folder": "/secreto/fotos", "message": "token=SECRET"}
        ]})
        self.assertEqual(len(result), 1)
        self.assertIn("2 transferência(s) aguardando confirmação", result[0])
        self.assertIn("3 pendente(s)", result[0])
        self.assertNotIn("/secreto", result[0])
        self.assertNotIn("SECRET", result[0])

    def test_stale_timer_is_visible(self):
        now = datetime(2026, 10, 19, 20, 0, tzinfo=timezone.utc)
        previous = (now - timedelta(minutes=22)).isoformat()
        self.assertIn("15 minutos", last_activity_age({"time": previous}, now))
        self.assertEqual(last_activity_age({"time": now.isoformat()}, now), "")

    def test_invalid_time_does_not_crash(self):
        self.assertEqual(last_activity_age({"time": "broken-date"}), "")


if __name__ == "__main__":
    unittest.main()
