@echo off
chcp 65001 > nul
title PDF圧縮ツール

echo ========================================
echo  PDF圧縮ツール 起動中...
echo ========================================
echo.

:: Ghostscript チェック
where gswin64c > nul 2>&1
if %errorlevel% neq 0 (
  where gswin32c > nul 2>&1
  if %errorlevel% neq 0 (
    echo [エラー] Ghostscriptが見つかりません。
    echo.
    echo インストール方法:
    echo   方法1: winget install Ghostscript.Ghostscript
    echo   方法2: https://www.ghostscript.com/releases/gsdnld.html からダウンロード
    echo.
    echo インストール後、このファイルを再度実行してください。
    pause
    exit /b 1
  )
)

echo [OK] Ghostscriptを確認しました。

:: Python チェック
where python > nul 2>&1
if %errorlevel% neq 0 (
  echo [エラー] Pythonが見つかりません。
  echo   https://www.python.org/ からPython 3.8以上をインストールしてください。
  pause
  exit /b 1
)

echo [OK] Pythonを確認しました。

:: Flask インストール
python -c "import flask" > nul 2>&1
if %errorlevel% neq 0 (
  echo [情報] Flaskをインストールしています...
  pip install flask
  if %errorlevel% neq 0 (
    echo [エラー] Flaskのインストールに失敗しました。
    pause
    exit /b 1
  )
)

echo [OK] Flaskを確認しました。
echo.
echo ブラウザで http://localhost:5000 を開きます...
echo 終了するにはこのウィンドウを閉じるか Ctrl+C を押してください。
echo.

:: ブラウザを2秒後に開く（バックグラウンド）
start "" /b cmd /c "timeout /t 2 > nul && start http://localhost:5000"

:: アプリ起動
python app.py

pause
