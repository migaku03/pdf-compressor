# PDF圧縮ツール

ローカルで完結するPDF圧縮ツールです。  
ファイルは外部に一切送信されません。Ghostscriptを使って高品質な圧縮を行います。

---

## 必要環境

- **Python** 3.8以上
- **Ghostscript**（別途インストールが必要）
- **NiceGUI**（起動スクリプトが自動インストール）

---

## Ghostscriptのインストール

### Mac
```bash
brew install ghostscript
```

### Windows
```
winget install Ghostscript.Ghostscript
```
または [公式サイト](https://www.ghostscript.com/releases/gsdnld.html) からインストーラーをダウンロード。

### Linux（Ubuntu / Debian）
```bash
sudo apt install ghostscript
```

### Linux（Fedora / RHEL）
```bash
sudo dnf install ghostscript
```

---

## 起動方法

### Mac / Linux

1. ターミナルで実行権限を付与（初回のみ）:
   ```bash
   chmod +x run.sh
   ```
2. `run.sh` をダブルクリック、またはターミナルで実行:
   ```bash
   ./run.sh
   ```

### Windows

`run.bat` をダブルクリック。

---

起動するとブラウザが自動的に `http://localhost:8080` を開きます（使用中の場合は8081）。

---

## 機能説明

### ファイル / フォルダ入力

- テキスト欄にファイルパスまたはフォルダパスを直接入力して「追加」
- 「ファイル参照」ボタンでダイアログからPDFを複数選択
- 「フォルダ参照」ボタンでフォルダを選択（直下の `*.pdf` を全て対象）
- 選択済みファイルは一覧表示され、個別に削除可能

### 圧縮率スライダー

| スライダー値 | Ghostscript設定 | 用途 |
|---|---|---|
| 0.9 | `/printer` | 印刷用高品質 |
| 0.7〜0.8 | `/ebook` | 電子書籍向け中品質 |
| 0.4〜0.6 | `/screen` | スクリーン表示向け低解像度 |
| 0.1〜0.3 | `/screen` + 72dpi | 最大圧縮 |

### 出力モード

- **OFF（デフォルト）**: 元ファイルと同ディレクトリに `_SD.pdf` を作成  
  例: `document.pdf` → `document_SD.pdf`
- **ON（上書き）**: 一時ファイル経由で元ファイルを圧縮済みで置き換え（安全）

### 結果表示

圧縮完了後、各ファイルの処理前サイズ・処理後サイズ・削減率・出力先・成功/失敗をテーブルで表示します。
