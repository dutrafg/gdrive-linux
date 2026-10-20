import tempfile
import os
import json
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
        digest = "a" * 32
        run.return_value.stdout = json.dumps([{"Path": "a.txt", "Hashes": {"MD5": digest}, "Size": 3}])
        self.assertEqual(remote_inventory("drive")["a.txt"], ("md5", digest))


    def test_rejects_control_paths_and_overlong_components(self):
        for value in ("hello\nworld", "a\r.txt", "a\tb", "x\x7f", "a/" + "z"*256,
                      "a/" + "x"*4097, "a/./b", "a/../b", "a//b"):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                validate_relative(value)

    def test_does_not_follow_symlink_root_or_hash_symlinked_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            selected = root / "root"
            selected.mkdir()
            (selected / "regular.txt").write_text("hello")
            link = root / "mirror-link"
            link.symlink_to(selected, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "link simbólico"):
                local_inventory(link)
            (selected / "unsafe.txt").symlink_to(root / "outside.txt")
            found = local_inventory(selected)
            self.assertEqual(list(found), ["regular.txt"])

    def test_does_not_hash_hardlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "file").write_text("sensitive")
            os.link(root / "file", root / "link")
            with self.assertRaisesRegex(ValueError, "links rígidos"):
                local_inventory(root)

    @patch("sync_plan.subprocess.run")
    def test_rejects_bad_hashes_and_duplicate_cloud_names(self, run):
        valid = {"Path": "a.txt", "Hashes": {"MD5": "b"*32}}
        cases = [
            [{"Path": "a.txt", "Hashes": {"MD5": "invalid"}}],
            [{"Path": "a.txt", "Hashes": {"SHA-256": "x"*64}}],
            [valid, valid],
            [{"Path": "bad\nname", "Hashes": {"MD5": "b"*32}}],
            [{"Path": "one", "Hashes": ["not-a-dict"]}],
            [{"Hashes": {"MD5": "b"*32}}],
            [None],
        ]
        for records in cases:
            with self.subTest(records=records), self.assertRaises(ValueError):
                run.return_value.stdout = json.dumps(records)
                remote_inventory("drive")

    @patch("sync_plan.subprocess.run")
    def test_sha256_remote_stays_incomparable_to_local_md5(self, run):
        run.return_value.stdout = json.dumps([
            {"Path": "content.bin", "Hashes": {"SHA-256": "a"*64}}
        ])
        remote = remote_inventory("drive")
        self.assertEqual(remote["content.bin"], ("sha256", "a"*64))
        from sync_plan import conservative_plan
        self.assertEqual(conservative_plan({"content.bin": ("md5", "b"*32)}, remote).conflicts,
                         ("content.bin",))

if __name__ == "__main__":
    unittest.main()
