import tempfile
import unittest
from unittest.mock import patch
import rclone_backend as b

class BackendTests(unittest.TestCase):
    def test_remote(self):
        self.assertEqual(b.remote_path('meudrive', 'Fotos'), 'meudrive:Fotos')
    def test_traversal(self):
        for path in ('../secret', '/root', '..\\\\secret', 'bad\\\\path'):
            with self.assertRaises(ValueError): b.remote_path('meudrive', path)
    def test_bad_remote(self):
        with self.assertRaises(ValueError): b.remote_path('foo:bar')
    def test_rejects_flag_like_and_control_names(self):
        for name in ("-config", "\x00evil", "bad\nremote", None):
            with self.subTest(name=name), self.assertRaises(ValueError):
                b.remote_path(name)

    @patch('rclone_backend.subprocess.run')
    def test_list_remotes_ignores_flag_like_name(self, run):
        run.return_value.stdout = 'valid:\n--config:\nsecond:\n'
        self.assertEqual(b.list_remotes(), ['valid', 'second'])

    def test_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(b.copy_command('drive', folder, 'download')[:3], ['rclone', 'copy', 'drive:'])
    @patch('rclone_backend.subprocess.run')
    def test_search_files_filters_paths(self, run):
        run.return_value.stdout = ('[{"Path":"Documents/Estudo.pdf","Size":100},'
                                   '{"Path":"Fotos/photo.jpg","Size":200}]')
        found = b.search_files("drive", "ESTUDO")
        self.assertEqual(found[0]["name"], "Documents/Estudo.pdf")
        self.assertEqual(len(found), 1)

    def test_search_minimum_length(self):
        with self.assertRaises(ValueError):
            b.search_files("drive", "a")

    @patch('rclone_backend.subprocess.run')
    def test_lsjson(self, run):
        run.return_value.stdout = '[{"Name":"Fotos","IsDir":true,"Size":0},{"Name":"a.txt","IsDir":false,"Size":10}]'
        self.assertEqual(b.list_files('drive')[0]['name'], 'Fotos')

    @patch('rclone_backend.subprocess.run')
    def test_lsjson_invalid(self, run):
        run.return_value.stdout = '{}'
        with self.assertRaises(ValueError): b.list_files('drive')

    @patch('rclone_backend.subprocess.run')
    def test_list(self, run):
        run.return_value.stdout = 'drive:\nother:\n'
        self.assertEqual(b.list_remotes(), ['drive', 'other'])

if __name__ == '__main__':
    unittest.main()
class AutomaticCopySafetyTests(unittest.TestCase):
    def test_automatic_download_preserves_newer_files(self):
        import tempfile
        from pathlib import Path
        from rclone_backend import copy_command
        with tempfile.TemporaryDirectory() as folder:
            cmd = copy_command("drive", Path(folder), "download", preserve_newer=True)
            self.assertIn("--update", cmd)

    def test_automatic_upload_is_rejected(self):
        import tempfile
        from pathlib import Path
        from rclone_backend import copy_command
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                copy_command("drive", Path(folder), "upload", preserve_newer=True)



class NonDestructiveAutoDownloadTests(unittest.TestCase):
    def test_auto_download_skips_existing(self):
        with tempfile.TemporaryDirectory() as folder:
            cmd = b.copy_command('drive', folder, 'download', skip_existing=True)
            self.assertIn('--ignore-existing', cmd)

    def test_manual_upload_can_preserve_existing_cloud_files(self):
        with tempfile.TemporaryDirectory() as folder:
            command = b.copy_command('drive', folder, 'upload', skip_existing=True)
            self.assertIn('--ignore-existing', command)
            self.assertEqual(command[1], 'copy')
