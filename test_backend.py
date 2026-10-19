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
    def test_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(b.copy_command('drive', folder, 'download')[:3], ['rclone', 'copy', 'drive:'])
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
