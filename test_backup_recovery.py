import tempfile
import unittest
from pathlib import Path

from backup_recovery import (
    RecoveryItem, list_local_backups, restore_local_backup, recovery_root)
from background_sync import job_key


class RecoveryTests(unittest.TestCase):
    def test_list_only_matching_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mirror=root/"mirror"
            mirror.mkdir()
            first=root/"backups"/job_key("drive",mirror)/"v1"/"report.txt"
            first.parent.mkdir(parents=True)
            first.write_text("old",encoding="utf-8")
            another=root/"backups"/job_key("other",mirror)/"v1"/"private.txt"
            another.parent.mkdir(parents=True)
            another.write_text("secret",encoding="utf-8")
            items=list_local_backups("drive",mirror,root/"backups")
            self.assertEqual(len(items),1)
            self.assertIn("report.txt",items[0].relative)
            self.assertNotIn("private",items[0].relative)

    def test_restore_never_overwrites_user_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            old=root/"old.txt"
            old.write_text("archived",encoding="utf-8")
            entry=RecoveryItem(old,"v1/old.txt","archive")
            dest=root/"restore"
            found=restore_local_backup(entry,dest)
            self.assertEqual(found.read_text(encoding="utf-8"),"archived")
            found.write_text("user newer",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"Já existe"):
                restore_local_backup(entry,dest)
            self.assertEqual(found.read_text(encoding="utf-8"),"user newer")
            self.assertTrue(old.exists())

    def test_refuses_symlink_as_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            link=root/"linked"
            link.symlink_to("/etc/passwd")
            item=RecoveryItem(link,"safe.txt","safe")
            with self.assertRaisesRegex(ValueError,"simbólico"):
                restore_local_backup(item,root/"recovered")

    def test_prevent_restore_outside_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            old=root/"old.txt"
            old.write_text("secret",encoding="utf-8")
            item=RecoveryItem(old,"../escape","escape")
            with self.assertRaises(ValueError):
                restore_local_backup(item,root/"restored")
            self.assertFalse((root/"escape").exists())


if __name__=="__main__":
    unittest.main()
