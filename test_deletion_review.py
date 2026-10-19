import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from deletion_review import find_deletions, load_candidates, archive_deletion
from background_sync import save_private_json, job_key

SAME = ("md5", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
EDITED = ("md5", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")

class DeletionPlanTests(unittest.TestCase):
    def test_deleted_local_cloud_still_exists(self):
        self.assertEqual(find_deletions({}, {"doc.txt": SAME},
                                        {"doc.txt": SAME[1]}),
                         [("doc.txt", "local")])

    def test_deleted_cloud_local_still_exists(self):
        self.assertEqual(find_deletions({"doc.txt": SAME}, {},
                                        {"doc.txt": SAME[1]}),
                         [("doc.txt", "cloud")])

    def test_does_not_archive_modified_survivor(self):
        self.assertEqual(find_deletions({"doc.txt": EDITED}, {},
                                        {"doc.txt": SAME[1]}), [])

    def test_no_baseline_no_delete(self):
        self.assertEqual(find_deletions({"doc.txt": SAME}, {}, {}), [])

class DeletionRcloneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.local = self.root / "local"
        self.cloud = self.root / "cloud"
        self.state = self.root / "state"
        self.backup = self.root / "backup"
        self.local.mkdir()
        self.cloud.mkdir()

    @patch("deletion_review.list_remotes", return_value=["demo"])
    @patch("deletion_review.inventories")
    def test_local_archive_preserves_bytes(self, inv, remotes):
        target = self.local / "keep.docx"
        target.write_text("original", encoding="utf-8")
        inv.return_value = ({"keep.docx": SAME}, {})
        self.state.mkdir()
        save_private_json(self.state / (job_key("demo", self.local) + ".json"),
                          {"md5": {"keep.docx": SAME[1]}})
        archived = archive_deletion("demo", self.local, "keep.docx", "cloud",
                                    state_base=self.state, backup_base=self.backup)
        self.assertFalse(target.exists())
        self.assertEqual(Path(archived).read_text(encoding="utf-8"), "original")
        self.assertEqual(load_snapshot(self.state, self.local)["md5"], {})

    @patch("deletion_review.list_remotes", return_value=["demo"])
    @patch("deletion_review.subprocess.run")
    @patch("deletion_review.inventories")
    def test_remote_archive_command_is_moveto(self, inv, run, remotes):
        inv.return_value = ({}, {"doc.docx": SAME})
        run.return_value.returncode = 0
        self.state.mkdir()
        save_private_json(self.state / (job_key("demo", self.local) + ".json"),
                          {"md5": {"doc.docx": SAME[1]}})
        archived = archive_deletion("demo", self.local, "doc.docx", "local",
                                    state_base=self.state, backup_base=self.backup)
        self.assertEqual(run.call_args.args[0][0:2], ["rclone", "moveto"])
        self.assertIn("archived-deletions", archived)

def load_snapshot(state, folder):
    from background_sync import read_json
    return read_json(state / (job_key("demo", folder) + ".json"))

if __name__ == "__main__":
    unittest.main()
