import unittest
from ui_kit import format_size

class FormatSizeTests(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(format_size(0), "0 B")
        self.assertEqual(format_size(1024), "1.0 KB")

    def test_invalid(self):
        self.assertEqual(format_size(None), "—")
        self.assertEqual(format_size(-10), "—")

if __name__ == "__main__":
    unittest.main()
