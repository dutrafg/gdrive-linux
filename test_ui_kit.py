import unittest
from ui_kit import format_size
from pathlib import Path
from gi.repository import Gtk

class FormatSizeTests(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(format_size(0), "0 B")
        self.assertEqual(format_size(1024), "1.0 KB")

    def test_css_loads(self):
        errors = []
        css = Gtk.CssProvider()
        css.connect("parsing-error", lambda _provider, _section, error: errors.append(error.message))
        css.load_from_path(str(Path(__file__).with_name("style.css")))
        self.assertEqual(errors, [], "GTK4 CSS parsing errors")

    def test_invalid(self):
        self.assertEqual(format_size(None), "—")
        self.assertEqual(format_size(-10), "—")

if __name__ == "__main__":
    unittest.main()
