#!/usr/bin/env bash
# Drive para Linux: deterministic local Debian packaging, no root or network.
set -euo pipefail
cd "$(dirname "$0")"
version="$(sed -n 's/^VERSION = "\([^"]*\)"$/\1/p' gdrive-linux)"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Erro: VERSION inválida no gdrive-linux" >&2
  exit 1
fi
command -v dpkg-deb >/dev/null || { echo "Instale dpkg-deb para criar o pacote." >&2; exit 1; }
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
pkg="$work/pkg"
mkdir -p "$pkg/DEBIAN" "$pkg/usr/bin" "$pkg/usr/share/gdrive-linux" "$pkg/usr/share/applications" "$pkg/usr/lib/systemd/user"
for file in gdrive-linux rclone_backend.py settings.py progress.py google_oauth.py sync_plan.py safe_sync.py ui_kit.py style.css background_sync.py backup_recovery.py rclone_config.py sync_display.py mount_drive.py mount_health.py mount_checks.py photos_export.py desktop_files.py deletion_review.py diagnostics.py rclone_errors.py mount_autostart.py sync_filters.py sync_profiles.py filemanager_bookmarks.py google_docs_export.py tray_indicator.py tray_autostart.py; do
  test -f "$file" || { echo "Arquivo ausente: $file" >&2; exit 1; }
  cp "$file" "$pkg/usr/share/gdrive-linux/$file"
done
printf '%s\n' '#!/bin/sh' 'exec /usr/bin/python3 /usr/share/gdrive-linux/gdrive-linux "$@"' > "$pkg/usr/bin/gdrive-linux"
chmod 755 "$pkg/usr/bin/gdrive-linux"
cp gdrive-linux-sync.service gdrive-linux-sync.timer gdrive-linux-mount.service "$pkg/usr/lib/systemd/user/"
cp gdrive-linux-indicator.desktop "$pkg/usr/share/applications/"
cat > "$pkg/DEBIAN/control" <<EOF
Package: gdrive-linux
Version: $version
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-gi, gir1.2-gtk-4.0, rclone, fuse3
Recommends: gir1.2-gtk-3.0, gir1.2-ayatanaappindicator3-0.1
Maintainer: Drive para Linux <noreply@example.invalid>
Description: Cliente GTK4 para Google Drive usando rclone
EOF
cat > "$pkg/usr/share/applications/gdrive-linux.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Drive para Linux
Comment=Cliente Google Drive com rclone
Exec=gdrive-linux
Icon=folder-remote
Categories=Network;FileTransfer;
StartupNotify=true
Terminal=false
EOF
filename="gdrive-linux_${version}_all.deb"
dpkg-deb --root-owner-group --build "$pkg" "$filename"
test "$(dpkg-deb -f "$filename" Version)" = "$version"
echo "Pacote criado: $(pwd)/$filename"
