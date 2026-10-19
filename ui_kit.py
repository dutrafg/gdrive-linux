"""Small GTK4 component helpers shared by the desktop UI."""
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


def label(text, css=None, wrap=False, hexpand=False):
    widget = Gtk.Label(label=text)
    widget.set_xalign(0)
    widget.set_wrap(wrap)
    widget.set_hexpand(hexpand)
    if css:
        widget.add_css_class(css)
    return widget


def card(title, description="", icon=None):
    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    outer.add_css_class("drive-card")
    heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    if icon:
        image = Gtk.Image.new_from_icon_name(icon)
        image.set_pixel_size(22)
        image.add_css_class("drive-card-icon")
        heading.append(image)
    heading.append(label(title, "drive-card-title", hexpand=True))
    outer.append(heading)
    if description:
        outer.append(label(description, "drive-muted", wrap=True))
    return outer


def action(text, callback=None, icon=None, primary=False, destructive=False):
    button = Gtk.Button()
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
    row.set_halign(Gtk.Align.CENTER)
    if icon:
        image = Gtk.Image.new_from_icon_name(icon)
        image.set_pixel_size(17)
        row.append(image)
    row.append(Gtk.Label(label=text))
    button.set_child(row)
    button.add_css_class("drive-primary" if primary else "drive-secondary")
    if destructive:
        button.add_css_class("drive-danger")
    if callback:
        button.connect("clicked", callback)
    return button


def nav(text, icon, callback):
    button = Gtk.Button()
    inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=13)
    inner.append(Gtk.Image.new_from_icon_name(icon))
    inner.append(label(text))
    button.set_child(inner)
    button.add_css_class("drive-nav")
    button.connect("clicked", callback)
    return button


def format_size(number):
    try:
        size = float(number)
        if size < 0:
            return "—"
    except (TypeError, ValueError, OverflowError):
        return "—"
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024 or unit == "PB":
            return (str(int(size)) if unit == "B" else f"{size:.1f}") + " " + unit
        size /= 1024


def section_title(text, subtitle=None):
    container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    container.append(label(text, "drive-section-title"))
    if subtitle:
        container.append(label(subtitle, "drive-muted", wrap=True))
    return container


def row(*items):
    container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    for item in items:
        container.append(item)
    return container

def button_flow(*buttons):
    """Wrap action buttons instead of clipping them in narrow GTK4 cards."""
    flow = Gtk.FlowBox()
    flow.set_selection_mode(Gtk.SelectionMode.NONE)
    flow.set_min_children_per_line(1)
    flow.set_max_children_per_line(3)
    flow.set_column_spacing(8)
    flow.set_row_spacing(8)
    flow.set_homogeneous(False)
    flow.set_halign(Gtk.Align.START)
    for button in buttons:
        flow.insert(button, -1)
    return flow
