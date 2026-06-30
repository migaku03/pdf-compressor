@echo off
chcp 65001 > nul
title PDF圧縮ツール

echo ========================================
echo  PDF圧縮ツール 起動中...
echo ========================================
echo.

:: ── Python check ─────────────────────────────────────────────────────────────
where python > nul 2>&1
if %errorlevel% neq 0 (
  echo [エラー] Pythonが見つかりません。
  echo   https://www.python.org/ からPython 3.8以上をインストールしてください。
  pause
  exit /b 1
)
echo [OK] Pythonを確認しました。

:: ── NiceGUI check / install ──────────────────────────────────────────────────
python -c "import nicegui" > nul 2>&1
if %errorlevel% neq 0 (
  echo [情報] NiceGUIをインストールしています...
  pip install nicegui
  if %errorlevel% neq 0 (
    echo [エラー] NiceGUIのインストールに失敗しました。
    pause
    exit /b 1
  )
)
echo [OK] NiceGUIを確認しました。

:: ── Ghostscript check (warning only) ─────────────────────────────────────────
set GS_FOUND=0
where gswin64c > nul 2>&1
if %errorlevel% equ 0 set GS_FOUND=1
where gswin32c > nul 2>&1
if %errorlevel% equ 0 set GS_FOUND=1

if "%GS_FOUND%"=="0" (
  echo.
  echo [警告] Ghostscriptが見つかりません。圧縮機能が使えません。
  echo   インストール方法:
  echo     winget install Ghostscript.Ghostscript
  echo   または https://www.ghostscript.com/releases/gsdnld.html からダウンロード
  echo.
) else (
  echo [OK] Ghostscriptを確認しました。
)

echo.
echo ブラウザが自動で開きます。終了するにはこのウィンドウを閉じてください。
echo.

:: ── Launch ────────────────────────────────────────────────────────────────────
python app.py

pause
