import unittest
from ui_kit import format_size, button_flow
from pathlib import Path
from gi.repository import Gtk

def iter_children(widget):
    child = widget.get_first_child()
    while child is not None:
        yield child
        child = child.get_next_sibling()

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

    def test_buttons_wrap_without_selection(self):
        buttons = [Gtk.Button(label=text) for text in ("Escolher", "Abrir", "Criar pasta")]
        flow = button_flow(*buttons)
        self.assertEqual(flow.get_max_children_per_line(), 3)
        self.assertEqual(flow.get_selection_mode(), Gtk.SelectionMode.NONE)
        self.assertEqual(len([x for x in iter_children(flow)]), 3)

    def test_invalid(self):
        self.assertEqual(format_size(None), "—")
        self.assertEqual(format_size(-10), "—")

if __name__ == "__main__":
    unittest.main()
