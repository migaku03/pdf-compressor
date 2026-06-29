# PDF圧縮ツール

ローカルで完結するPDF圧縮Webアプリです。  
ファイルは外部に一切送信されません。Ghostscriptを使って高品質な圧縮を行います。

<!-- screenshot -->

---

## 必要環境

- **Python** 3.8以上
- **Ghostscript**（別途インストールが必要）

---

## Ghostscriptのインストール

### Windows
```
winget install Ghostscript.Ghostscript
```
または [公式サイト](https://www.ghostscript.com/releases/gsdnld.html) からインストーラーをダウンロード。

### Mac
```bash
brew install ghostscript
```

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

### Windows
`run.bat` をダブルクリック。  
Flask が未インストールの場合は自動でインストールされます。

### Mac / Linux
ターミナルで以下を実行して実行権限を付与してからダブルクリック（または実行）。

```bash
chmod +x run.sh
./run.sh
```

起動後、ブラウザが自動的に `http://localhost:5000` を開きます。  
ポート5000が使用中の場合は5001番に自動フォールバックします。

---

## 機能説明

### ファイル入力
- PDFファイルを複数選択またはドラッグ＆ドロップで入力
- フォルダを指定するとフォルダ内の全PDFを一括処理（サブフォルダは除く）

### 圧縮率スライダー
| スライダー値 | Ghostscript設定 | 用途 |
|---|---|---|
| 0.9 | `/printer` | 印刷用高品質 |
| 0.7〜0.8 | `/ebook` | 電子書籍向け中品質 |
| 0.4〜0.6 | `/screen` | スクリーン表示向け低解像度 |
| 0.1〜0.3 | `/screen` + 72dpi | 最大圧縮 |

### 出力モード
- **OFF（デフォルト）**: 元ファイル名に `_SD` を付けて同じフォルダに保存  
  例: `document.pdf` → `document_SD.pdf`
- **ON（上書き）**: 元のファイルを圧縮済みファイルで置き換え  
  ※ 一時ファイルに書き出してから置き換えるため、処理中断しても元ファイルは保持されます

### 結果表示
処理完了後、各ファイルの処理前サイズ・処理後サイズ・削減率・成功/失敗をテーブルで表示します。
