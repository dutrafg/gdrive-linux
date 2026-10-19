import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from filemanager_bookmarks import set_bookmark, bookmark_entry
from google_docs_export import export_command, export_folder, assert_not_inside_mirror, export_documents
from tray_indicator import status_summary
from tray_autostart import set_indicator_autostart, indicator_enabled
from mount_autostart import update_autostart

class FileManagerTests(unittest.TestCase):
    def test_add_remove_preserves_other_bookmarks(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            store = base/"bookmarks"
            store.write_text("file:///home/me/Documents Documents\n")
            set_bookmark("mydrive", True, store, base/"mounts")
            self.assertIn("Drive - mydrive", store.read_text())
            set_bookmark("mydrive", True, store, base/"mounts")
            self.assertEqual(store.read_text().count("Drive - mydrive"), 1)
            set_bookmark("mydrive", False, store, base/"mounts")
            self.assertIn("Documents Documents", store.read_text())
            self.assertNotIn("Drive - mydrive", store.read_text())

class DocsTests(unittest.TestCase):
    def test_odf_office_and_pdf_formats(self):
        with tempfile.TemporaryDirectory() as root:
            for format_name, suffix in (("libreoffice", "odt"), ("office", "docx"),
                                        ("pdf", "pdf")):
                with self.subTest(format_name=format_name):
                    cmd = export_command("drive", Path(root)/"exports", format_name)
                    self.assertIn("--drive-export-formats", cmd)
                    self.assertIn("--ignore-existing", cmd)
                    self.assertIn("*."+suffix, cmd)
                    self.assertNotIn("sync", cmd)

    def test_export_is_outside_mirror(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            with self.assertRaises(ValueError):
                assert_not_inside_mirror(base/"GoogleDrive"/"export", base/"GoogleDrive")

    @patch("google_docs_export.subprocess.run")
    def test_export_requires_actual_drive_backend(self, run):
        with tempfile.TemporaryDirectory() as root:
            run.return_value.returncode = 0
            run.return_value.stdout = '{"Name":"alias"}'
            with self.assertRaises(ValueError):
                export_documents("alias", Path(root)/"mirror", home=root)
            self.assertEqual(run.call_count, 1)

    @patch("google_docs_export.subprocess.run")
    def test_office_export_is_read_only_for_remote(self, run):
        with tempfile.TemporaryDirectory() as root:
            run.return_value.returncode = 0
            run.return_value.stdout = '{"Name":"drive"}'
            result = export_documents("drive", Path(root)/"mirror", home=root, dry_run=True)
            self.assertTrue(result["preview"])
            self.assertTrue(run.call_args.args[0][-1] == "--dry-run")

class TrayTests(unittest.TestCase):
    def test_states_and_no_secrets(self):
        self.assertIn("Sincronizado", status_summary({"state":"ok","pending":0})[0])
        self.assertTrue(status_summary({"state":"quota"})[1])
        self.assertTrue(status_summary({"state":"conflicts"})[1])

    def test_per_user_autostart(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            template = base/"template.desktop"
            template.write_text("[Desktop Entry]\nType=Application\nX-DriveLinux-Managed=true\n")
            self.assertTrue(set_indicator_autostart(True, source=template, home=base))
            self.assertTrue(indicator_enabled(home=base))
            self.assertFalse(set_indicator_autostart(False, source=template, home=base))
            self.assertFalse(indicator_enabled(home=base))

class AutoMountTests(unittest.TestCase):
    def test_enable_only_users_systemd(self):
        calls=[]
        def run(args, **kwargs):
            calls.append(args)
            return type("Result",(),{"returncode":0})()
        enabled, message = update_autostart(True, runner=run)
        self.assertTrue(enabled)
        self.assertEqual(calls[0][0:2], ["systemctl","--user"])
        self.assertEqual(calls[1][-2:], ["enable","gdrive-linux-mount.service"])
        self.assertIn("--no-block", calls[2])
        self.assertIn("sessão", message)

    def test_disable(self):
        calls=[]
        def run(args, **kwargs):
            calls.append(args)
            return type("Result",(),{"returncode":0})()
        enabled, _ = update_autostart(False, runner=run)
        self.assertFalse(enabled)
        self.assertIn("disable",calls[1])
        self.assertEqual(len(calls), 2)
        self.assertNotIn("stop", [item for cmd in calls for item in cmd])

if __name__ == "__main__":
    unittest.main()
