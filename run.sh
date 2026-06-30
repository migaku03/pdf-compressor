#!/usr/bin/env bash
set -e

echo "========================================"
echo " PDF圧縮ツール 起動中..."
echo "========================================"
echo ""

# ── Python check ─────────────────────────────────────────────────────────────
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    VER=$("$cmd" -c "import sys; print(sys.version_info.major, sys.version_info.minor)")
    MAJOR=$(echo "$VER" | awk '{print $1}')
    MINOR=$(echo "$VER" | awk '{print $2}')
    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 8 ]; then
      PYTHON="$cmd"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  echo "[エラー] Python 3.8以上が見つかりません。"
  echo "  https://www.python.org/ からインストールしてください。"
  exit 1
fi
echo "[OK] Python: $PYTHON"

# ── NiceGUI check / install ──────────────────────────────────────────────────
if ! "$PYTHON" -c "import nicegui" &>/dev/null; then
  echo "[情報] NiceGUIをインストールしています..."
  "$PYTHON" -m pip install nicegui
fi
echo "[OK] NiceGUI を確認しました。"

# ── Ghostscript check (warning only) ────────────────────────────────────────
GS_FOUND=0
for gs_path in gs /opt/homebrew/bin/gs /usr/local/bin/gs /usr/bin/gs; do
  if command -v "$gs_path" &>/dev/null; then
    GS_FOUND=1
    break
  fi
done

if [ "$GS_FOUND" -eq 0 ]; then
  echo ""
  echo "[警告] Ghostscript が見つかりません。圧縮機能が使えません。"
  echo "  Mac:            brew install ghostscript"
  echo "  Ubuntu/Debian:  sudo apt install ghostscript"
  echo "  Fedora/RHEL:    sudo dnf install ghostscript"
  echo ""
else
  echo "[OK] Ghostscript を確認しました。"
fi

echo ""
echo "ブラウザが自動で開きます。終了するには Ctrl+C を押してください。"
echo ""

# ── Launch ───────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
"$PYTHON" app.py
