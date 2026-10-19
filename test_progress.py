import unittest
from progress import parse_progress

class ProgressTests(unittest.TestCase):
    def test_percentage(self):
        result = parse_progress("Transferred:  10 MiB / 20 MiB, 50%, 2 MiB/s, ETA 5s")
        self.assertEqual(result["percentage"], 50)
        self.assertEqual(result["speed"], "2 MiB/s")
    def test_invalid(self):
        self.assertIsNone(parse_progress("Transfer started"))
        self.assertIsNone(parse_progress("Transferred: 10 MiB, 150%"))

if __name__ == "__main__":
    unittest.main()
