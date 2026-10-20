import tempfile
import os
import stat
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

    def test_recovery_location_is_outside_selected_documents_mirror(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            documents = home / "Documents"
            documents.mkdir()
            alternative = recovery_root(home, mirror_folder=documents)
            self.assertTrue(str(alternative).startswith(str(home / ".local")))
            self.assertFalse(alternative.is_relative_to(documents))

    def test_recovery_rejects_custom_destination_inside_mirror(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mirror = root / "mirror"
            mirror.mkdir()
            source = root / "archived.txt"
            source.write_text("backup", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "destino está dentro"):
                restore_local_backup(RecoveryItem(source, "file.txt", "archive"),
                                     destination=mirror / "Recovered",
                                     mirror_folder=mirror)
            self.assertTrue(source.exists())

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


    def test_nested_recovery_creates_private_files_and_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.write_bytes(b"archive bytes")
            restored = restore_local_backup(
                RecoveryItem(source, "history/2026/nested.txt", "archive"), root / "out")
            self.assertEqual(restored.read_bytes(), b"archive bytes")
            self.assertEqual(stat.S_IMODE(restored.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(restored.parent.stat().st_mode), 0o700)

    def test_recovery_rejects_hardlinked_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "backup"
            source.write_text("protected")
            os.link(source, root / "alias")
            with self.assertRaisesRegex(ValueError, "independente"):
                restore_local_backup(RecoveryItem(source, "report.txt", "archived"), root / "out")
            self.assertFalse((root / "out" / "report.txt").exists())

    def test_recovery_refuses_symlinked_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "archive"
            source.write_text("safe")
            target = root / "target"
            target.mkdir()
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            (target / "linked").symlink_to(elsewhere, target_is_directory=True)
            with self.assertRaises((OSError, ValueError)):
                restore_local_backup(
                    RecoveryItem(source, "linked/escaped.txt", "archive"), target)
            self.assertFalse((elsewhere / "escaped.txt").exists())

    def test_recovery_root_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "backup.txt"
            source.write_text("ok")
            real = root / "real"
            real.mkdir()
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "simbólico"):
                restore_local_backup(RecoveryItem(source, "copy.txt", "safe"), link)



if __name__=="__main__":
    unittest.main()
