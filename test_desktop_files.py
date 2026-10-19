import tempfile
import unittest
from pathlib import Path
from desktop_files import find_openable_file

class DesktopFilesTests(unittest.TestCase):
    def test_find_local_office_doc(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mirror = root/"mirror"
            mirror.mkdir()
            doc = mirror/"relatorio.docx"
            doc.write_bytes(b"test")
            self.assertEqual(find_openable_file("relatorio.docx", mirror, "drive",
                                                online_root=root/"online"), doc)

    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            mirror = Path(tmp)
            self.assertIsNone(find_openable_file("missing.docx", mirror, "drive",
                                                  online_root=mirror/"online"))

    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                find_openable_file("../private.txt", tmp, "drive", online_root=Path(tmp))

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mirror = root/"mirror"
            mirror.mkdir()
            (mirror/"external.docx").symlink_to("/etc/passwd")
            self.assertIsNone(find_openable_file("external.docx", mirror, "drive"))

if __name__ == "__main__":
    unittest.main()
