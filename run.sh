#!/usr/bin/env bash
set -e

echo "========================================"
echo " PDF圧縮ツール 起動中..."
echo "========================================"
echo ""

# Ghostscript チェック
if ! command -v gs &>/dev/null; then
  echo "[エラー] Ghostscriptが見つかりません。"
  echo ""
  echo "インストール方法:"
  echo "  Mac:   brew install ghostscript"
  echo "  Ubuntu/Debian: sudo apt install ghostscript"
  echo "  Fedora/RHEL:   sudo dnf install ghostscript"
  echo ""
  echo "インストール後、このスクリプトを再度実行してください。"
  exit 1
fi
echo "[OK] Ghostscriptを確認しました。"

# Python チェック
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
echo "[OK] Pythonを確認しました: $PYTHON"

# Flask インストール
if ! "$PYTHON" -c "import flask" &>/dev/null; then
  echo "[情報] Flaskをインストールしています..."
  "$PYTHON" -m pip install flask
fi
echo "[OK] Flaskを確認しました。"

echo ""
echo "ブラウザで http://localhost:5000 を開きます..."
echo "終了するには Ctrl+C を押してください。"
echo ""

# ブラウザを2秒後に開く（バックグラウンド）
(
  sleep 2
  if command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:5000" &>/dev/null
  elif command -v open &>/dev/null; then
    open "http://localhost:5000"
  fi
) &

# アプリ起動
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
"$PYTHON" app.py
