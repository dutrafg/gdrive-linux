import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sync_plan import plan_sync, local_inventory, remote_inventory, validate_relative

class SyncPlanTests(unittest.TestCase):
    def test_separates_new_files_and_conflicts(self):
        plan = plan_sync({"local.txt": "a", "shared.txt": "one"},
                         {"remote.txt": "b", "shared.txt": "two"})
        self.assertEqual(plan.download, ("remote.txt",))
        self.assertEqual(plan.upload, ("local.txt",))
        self.assertEqual(plan.conflicts, ("shared.txt",))

    def test_identical_entries_are_unchanged(self):
        plan = plan_sync({"a": "same"}, {"a": "same"})
        self.assertEqual((plan.download, plan.upload, plan.conflicts), ((), (), ()))

    def test_local_inventory_hashes_content(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "a.txt").write_text("hello", encoding="utf-8")
            inventory = local_inventory(root)
            self.assertEqual(inventory["a.txt"][0], "md5")

    def test_matching_md5_not_conflict(self):
        from sync_plan import conservative_plan
        plan = conservative_plan({"a.txt": ("md5", "abc")}, {"a.txt": ("md5", "abc")})
        self.assertEqual(plan.conflicts, ())

    def test_unknown_hash_is_conflict(self):
        from sync_plan import conservative_plan
        plan = conservative_plan({"a.txt": ("md5", "abc")}, {"a.txt": ("metadata", "3", "today")})
        self.assertEqual(plan.conflicts, ("a.txt",))

    def test_rejects_traversal(self):
        for name in ("../private", "/absolute", "a\\b", ""):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_relative(name)

    @patch("sync_plan.subprocess.run")
    def test_remote_inventory(self, run):
        run.return_value.stdout = '[{"Path":"a.txt","Hashes":{"MD5":"abc"},"Size":3}]'
        self.assertEqual(remote_inventory("drive")["a.txt"], ("md5", "abc"))

if __name__ == "__main__":
    unittest.main()
