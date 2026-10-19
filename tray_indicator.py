"""Optional GTK3 StatusNotifier indicator for Zorin/GNOME/Ubuntu desktops.

Runs separately from the GTK4 application. Requires the system package
gir1.2-ayatanaappindicator3-0.1 (or compatible AppIndicator3).
"""
import subprocess
from pathlib import Path
from background_sync import read_json, STATE_BASE

def status_summary(status):
    state = status.get("state", "unknown") if isinstance(status, dict) else "unknown"
    if state == "ok":
        accounts = status.get("profiles")
        count = len(accounts) if isinstance(accounts, list) else 0
        prefix = (str(count) + " conta(s) • " if count else "")
        skipped = status.get("skipped_direction", 0)
        return (prefix + "Sincronizado" +
                (" (" + str(skipped) + " fora da direção)" if skipped else ""), False)
    if state == "partial":
        return str(status.get("pending", 0)) + " arquivo(s) aguardando próximos ciclos", False
    if state == "quota":
        return "Google Drive: limite da API (403)", True
    if state == "conflicts":
        return "Conflitos pendentes", True
    if state == "error":
        return "Falha de sincronização", True
    if state == "busy":
        return "Sincronizando", False
    return "Aguardando sincronização", False

def open_app():
    subprocess.Popen(["gdrive-linux"], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)

def sync_now():
    subprocess.Popen(["systemctl", "--user", "--no-block", "start",
                      "gdrive-linux-sync.service"], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)

def main():
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, GLib
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as Indicator
    except (ImportError, ValueError):
        try:
            gi.require_version("AppIndicator3", "0.1")
            from gi.repository import AppIndicator3 as Indicator
        except (ImportError, ValueError):
            return 1  # Desktop has no compatible tray; app still works.

    item = Indicator.Indicator.new(
        "gdrive-linux-indicator", "folder-sync",
        Indicator.IndicatorCategory.APPLICATION_STATUS)
    item.set_status(Indicator.IndicatorStatus.ACTIVE)
    menu = Gtk.Menu()
    status_item = Gtk.MenuItem(label="Drive para Linux: aguardando")
    status_item.set_sensitive(False)
    menu.append(status_item)
    open_item = Gtk.MenuItem(label="Abrir Drive para Linux")
    open_item.connect("activate", lambda *_: open_app())
    menu.append(open_item)
    sync_item = Gtk.MenuItem(label="Sincronizar agora")
    sync_item.connect("activate", lambda *_: sync_now())
    menu.append(sync_item)
    menu.append(Gtk.SeparatorMenuItem())
    quit_item = Gtk.MenuItem(label="Fechar indicador")
    quit_item.connect("activate", lambda *_: Gtk.main_quit())
    menu.append(quit_item)
    menu.show_all()
    item.set_menu(menu)

    def refresh():
        description, attention = status_summary(read_json(STATE_BASE / "latest.json"))
        status_item.set_label("Drive para Linux: " + description)
        item.set_status(Indicator.IndicatorStatus.ATTENTION if attention else
                        Indicator.IndicatorStatus.ACTIVE)
        return True

    refresh()
    GLib.timeout_add_seconds(30, refresh)
    Gtk.main()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
