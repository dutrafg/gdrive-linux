import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from photos_export import eligible_paths, validate_album, photos_copy_command, photos_backend, upload_media

class PhotosTests(unittest.TestCase):
    def test_album_validation(self):
        self.assertEqual(validate_album("Minhas Fotos"), "Minhas Fotos")
        for item in ("", "../segredos", "a/b", "..", "   "):
            with self.subTest(item=item), self.assertRaises(ValueError):
                validate_album(item)

    def test_local_media_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/"foto.JPG").write_bytes(b"abc")
            (root/"video.mp4").write_bytes(b"abc")
            (root/"private.txt").write_bytes(b"secret")
            self.assertEqual(eligible_paths(root), ["foto.JPG", "video.mp4"])

    def test_upload_command_is_non_destructive(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = photos_copy_command(tmp, "photos", "Drive para Linux")
            self.assertEqual(cmd[0:2], ["rclone", "copy"])
            self.assertIn("--ignore-existing", cmd)
            self.assertNotIn("delete", cmd)
            self.assertIn("photos:album/Drive para Linux", cmd)

    @patch("photos_export.subprocess.run")
    def test_backend_read_without_config_credentials(self, run):
        run.return_value.stdout = '{"Name":"google photos"}'
        self.assertEqual(photos_backend("photos"), "google photos")
        self.assertEqual(run.call_args.args[0][0:3],
                         ["rclone", "backend", "features"])

    @patch("photos_export.photos_backend", return_value="drive")
    def test_never_uploads_to_google_drive_by_mistake(self, kind):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/"foto.jpg").write_bytes(b"abc")
            with self.assertRaises(ValueError):
                upload_media(tmp, "my_drive", dry_run=False)

    @patch("photos_export.photos_backend", return_value="google photos")
    def test_preview_never_uploads(self, kind):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/"foto.jpg").write_bytes(b"abc")
            result = upload_media(tmp, "photos", dry_run=True)
            self.assertEqual(result["state"], "preview")
            self.assertEqual(result["candidates"], 1)

if __name__ == "__main__":
    unittest.main()
