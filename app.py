import asyncio
import glob
import os
import platform
import shutil
import socket
import subprocess
import tempfile

from nicegui import run, ui


# ── Ghostscript ──────────────────────────────────────────────────────────────

def find_ghostscript() -> str | None:
    for cmd in ['gs', '/opt/homebrew/bin/gs', '/usr/local/bin/gs',
                '/usr/bin/gs', 'gswin64c', 'gswin32c']:
        try:
            r = subprocess.run([cmd, '--version'], capture_output=True,
                               text=True, timeout=5)
            if r.returncode == 0:
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def get_gs_flags(ratio: float) -> list:
    if ratio >= 0.9:
        return ['-dPDFSETTINGS=/printer']
    elif ratio >= 0.7:
        return ['-dPDFSETTINGS=/ebook']
    elif ratio >= 0.4:
        return ['-dPDFSETTINGS=/screen']
    else:
        return ['-dPDFSETTINGS=/screen',
                '-dColorImageResolution=72',
                '-dGrayImageResolution=72']


def compress_pdf_sync(gs_cmd: str, src: str, dst: str, ratio: float):
    cmd = ([gs_cmd, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
             '-dNOPAUSE', '-dQUIET', '-dBATCH']
           + get_gs_flags(ratio)
           + [f'-sOutputFile={dst}', src])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return r.returncode == 0, r.stderr


def fmt_size(b: int) -> str:
    if b >= 1_048_576:
        return f'{b / 1_048_576:.2f} MB'
    return f'{b / 1024:.1f} KB'


# ── Native file / folder dialogs ─────────────────────────────────────────────
# macOS : asyncio.create_subprocess_exec でイベントループをブロックしない
# Windows: run.io_bound 経由で tkinter をワーカースレッドで実行

# ダイアログは System Events の tell ブロックに入れると画面に出ない。
# Finder をアクティブ化してから Standard Additions の choose file/folder を
# トップレベルで呼ぶことで macOS の標準ダイアログが表示される。
_SCRIPT_PICK_FILES = '''\
tell application "Finder" to activate
delay 0.3
set f to choose file of type {"pdf"} with multiple selections allowed
if class of f is list then
    set pathList to {}
    repeat with aFile in f
        set end of pathList to POSIX path of aFile
    end repeat
    set AppleScript's text item delimiters to linefeed
    return pathList as text
else
    return POSIX path of f
end if'''

_SCRIPT_PICK_FOLDER = '''\
tell application "Finder" to activate
delay 0.3
set f to choose folder
return POSIX path of f'''


async def _dialog_pick_files() -> list:
    """ファイル選択ダイアログ（non-blocking）。"""
    if platform.system() == 'Darwin':
        try:
            proc = await asyncio.create_subprocess_exec(
                'osascript', '-e', _SCRIPT_PICK_FILES,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            err_text = stderr.decode().strip()
            out_text = stdout.decode().strip()
            if proc.returncode != 0:
                # キャンセルは正常扱い（エラー通知不要）
                if err_text and 'cancel' not in err_text.lower():
                    ui.notify(f'ダイアログエラー: {err_text}', type='negative', timeout=8000)
                return []
            if not out_text:
                return []
            return [p.strip() for p in out_text.splitlines() if p.strip()]
        except Exception as exc:
            ui.notify(f'ダイアログ起動エラー: {exc}', type='negative', timeout=8000)
            return []
    else:
        def _win():
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            paths = filedialog.askopenfilenames(
                title='PDFファイルを選択',
                filetypes=[('PDF files', '*.pdf'), ('All files', '*.*')],
            )
            root.destroy()
            return list(paths)
        return await run.io_bound(_win)


async def _dialog_pick_folder() -> str:
    """フォルダ選択ダイアログ（non-blocking）。"""
    if platform.system() == 'Darwin':
        try:
            proc = await asyncio.create_subprocess_exec(
                'osascript', '-e', _SCRIPT_PICK_FOLDER,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            err_text = stderr.decode().strip()
            out_text = stdout.decode().strip()
            if proc.returncode != 0:
                if err_text and 'cancel' not in err_text.lower():
                    ui.notify(f'ダイアログエラー: {err_text}', type='negative', timeout=8000)
                return ''
            return out_text
        except Exception as exc:
            ui.notify(f'ダイアログ起動エラー: {exc}', type='negative', timeout=8000)
            return ''
    else:
        def _win():
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            path = filedialog.askdirectory(title='フォルダを選択')
            root.destroy()
            return path or ''
        return await run.io_bound(_win)


# ── Port helper ──────────────────────────────────────────────────────────────

def find_free_port(preferred: int = 8080) -> int:
    for port in [preferred, preferred + 1]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    return preferred


# ── UI ────────────────────────────────────────────────────────────────────────

gs_cmd = find_ghostscript()

selected_files: list = []
ratio_value: list = [0.5]      # mutable cell so closures share state
overwrite_mode: list = [False]


@ui.page('/')
def main_page():
    with ui.header().classes('bg-blue-700 text-white items-center px-4 py-2'):
        ui.label('PDF 圧縮ツール').classes('text-xl font-bold')

    with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-4'):

        # GS warning
        if not gs_cmd:
            with ui.card().classes('w-full border border-red-400 bg-red-50'):
                ui.label('⚠ Ghostscript が見つかりません').classes(
                    'text-red-700 font-bold text-base')
                ui.label('Mac:  brew install ghostscript').classes(
                    'font-mono text-sm text-red-600')
                ui.label('Windows:  winget install Ghostscript.Ghostscript').classes(
                    'font-mono text-sm text-red-600')

        # ── File input card ──────────────────────────────────────────────
        with ui.card().classes('w-full'):
            ui.label('ファイル / フォルダ').classes('font-bold text-gray-700 mb-1')
            ui.label(
                'ファイルパスまたはフォルダパスを入力して「追加」してください。'
                '複数パスは改行または ; で区切れます。'
            ).classes('text-xs text-gray-500 mb-2')
            ui.label(
                'Mac のヒント: Finder でファイルを選択し、右クリック → '
                '「パスのコピー」（Option キーを押しながら）でパスをコピーできます。'
            ).classes('text-xs text-gray-400 mb-2')

            path_input = ui.textarea(
                placeholder=(
                    '/Users/you/documents/report.pdf\n'
                    '/Users/you/documents/  ← フォルダも可（直下の*.pdfを全て追加）'
                ),
            ).classes('w-full').props('rows=3 outlined')

            file_list = ui.column().classes('w-full gap-1 mt-2')

            def refresh_list():
                file_list.clear()
                if not selected_files:
                    with file_list:
                        ui.label('ファイルが選択されていません').classes(
                            'text-gray-400 text-sm italic')
                    return
                with file_list:
                    for i, p in enumerate(selected_files):
                        with ui.row().classes('items-center gap-2 w-full'):
                            ui.label(f'• {os.path.basename(p)}').classes(
                                'text-sm flex-1 truncate')
                            size_str = fmt_size(os.path.getsize(p)) if os.path.exists(p) else '?'
                            ui.label(size_str).classes('text-xs text-gray-500 w-20 text-right')
                            ui.button(icon='close',
                                      on_click=lambda _, idx=i: remove_file(idx)
                                      ).props('flat dense size=xs color=negative')

            def remove_file(i: int):
                selected_files.pop(i)
                refresh_list()

            def add_from_input():
                raw = path_input.value.strip()
                if not raw:
                    ui.notify('パスを入力してください', type='warning')
                    return
                parts = [p.strip() for p in raw.replace(';', '\n').splitlines()
                         if p.strip()]
                added = 0
                for part in parts:
                    p = os.path.abspath(part)
                    if os.path.isdir(p):
                        for pdf in sorted(glob.glob(os.path.join(p, '*.pdf'))):
                            if pdf not in selected_files:
                                selected_files.append(pdf)
                                added += 1
                    elif os.path.isfile(p) and p.lower().endswith('.pdf'):
                        if p not in selected_files:
                            selected_files.append(p)
                            added += 1
                path_input.value = ''
                refresh_list()
                if added == 0:
                    ui.notify('PDFファイルが見つかりませんでした', type='warning')
                else:
                    ui.notify(f'{added} 件追加しました', type='positive')

            async def pick_files():
                paths = await _dialog_pick_files()
                if not paths:
                    return
                added = 0
                for p in paths:
                    p = os.path.abspath(p)
                    if p not in selected_files:
                        selected_files.append(p)
                        added += 1
                refresh_list()
                if added:
                    ui.notify(f'{added} 件追加しました', type='positive')

            async def pick_folder():
                folder = await _dialog_pick_folder()
                if not folder:
                    return
                folder = os.path.abspath(folder)
                added = 0
                for pdf in sorted(glob.glob(os.path.join(folder, '*.pdf'))):
                    if pdf not in selected_files:
                        selected_files.append(pdf)
                        added += 1
                refresh_list()
                if added:
                    ui.notify(f'{added} 件追加しました', type='positive')
                else:
                    ui.notify('フォルダ内にPDFが見つかりませんでした', type='warning')

            with ui.row().classes('gap-2 mt-2 flex-wrap'):
                ui.button('追加', icon='add', on_click=add_from_input).props('dense')
                ui.button('ファイル参照', icon='folder_open',
                          on_click=pick_files).props('dense')
                ui.button('フォルダ参照', icon='folder',
                          on_click=pick_folder).props('dense')
                ui.button('リストをクリア', icon='delete_sweep',
                          on_click=lambda: (selected_files.clear(), refresh_list())
                          ).props('dense color=negative flat')

            refresh_list()

        # ── Ratio card ───────────────────────────────────────────────────
        with ui.card().classes('w-full'):
            ui.label('圧縮率').classes('font-bold text-gray-700')

            ratio_label = ui.label(
                f'{ratio_value[0]:.1f}倍（約{int(ratio_value[0] * 100)}%）'
            ).classes('text-blue-600 font-mono text-base')

            def on_ratio_change(e):
                ratio_value[0] = round(float(e.value), 1)
                ratio_label.set_text(
                    f'{ratio_value[0]:.1f}倍（約{int(ratio_value[0] * 100)}%）')

            ui.slider(min=0.1, max=0.9, step=0.1,
                      value=ratio_value[0],
                      on_change=on_ratio_change).classes('w-full')

            with ui.row().classes('text-xs text-gray-500 gap-4 flex-wrap mt-1'):
                ui.label('0.1〜0.3: 最大圧縮（72 dpi）')
                ui.label('0.4〜0.6: スクリーン')
                ui.label('0.7〜0.8: ebook')
                ui.label('0.9: 高品質印刷')

        # ── Overwrite card ───────────────────────────────────────────────
        with ui.card().classes('w-full'):
            mode_label = ui.label('出力モード: 別名保存（_SD）').classes(
                'font-bold text-gray-700')

            def on_overwrite(e):
                overwrite_mode[0] = e.value
                mode_label.set_text(
                    '出力モード: 上書き保存' if e.value else '出力モード: 別名保存（_SD）')

            ui.switch('上書き保存 ON', value=False,
                      on_change=on_overwrite).classes('mt-1')

            ui.label(
                'OFF: 同ディレクトリに _SD.pdf を作成  ／  ON: 元ファイルを置き換え（一時ファイル経由で安全に処理）'
            ).classes('text-xs text-gray-500 mt-1')

        # ── Progress ─────────────────────────────────────────────────────
        progress_row = ui.column().classes('w-full gap-1')
        with progress_row:
            progress_bar = ui.linear_progress(
                value=0, show_value=False).classes('w-full')
            progress_label = ui.label('').classes('text-sm text-gray-600')
        progress_row.visible = False

        # ── Result table ─────────────────────────────────────────────────
        result_area = ui.column().classes('w-full')

        # ── Run button ───────────────────────────────────────────────────
        async def do_compress():
            if not gs_cmd:
                ui.notify('Ghostscriptが見つかりません', type='negative')
                return
            if not selected_files:
                ui.notify('ファイルを選択してください', type='warning')
                return

            run_btn.disable()
            progress_row.visible = True
            result_area.clear()

            results = []
            total = len(selected_files)

            for idx, src in enumerate(list(selected_files)):
                fname = os.path.basename(src)
                progress_label.set_text(
                    f'処理中 ({idx + 1}/{total}): {fname}')
                progress_bar.set_value(idx / total)

                tmp_out = None
                try:
                    original_size = os.path.getsize(src)
                    with tempfile.NamedTemporaryFile(suffix='.pdf',
                                                     delete=False) as f:
                        tmp_out = f.name

                    ok, err = await run.io_bound(
                        compress_pdf_sync, gs_cmd, src, tmp_out,
                        ratio_value[0])

                    if ok and os.path.exists(tmp_out) \
                            and os.path.getsize(tmp_out) > 0:
                        compressed_size = os.path.getsize(tmp_out)
                        pct = ((1 - compressed_size / original_size) * 100
                               if original_size > 0 else 0)

                        if overwrite_mode[0]:
                            dest = src
                        else:
                            base, ext = os.path.splitext(src)
                            dest = base + '_SD' + ext

                        shutil.move(tmp_out, dest)
                        tmp_out = None

                        results.append({
                            'filename': fname,
                            'orig': fmt_size(original_size),
                            'comp': fmt_size(compressed_size),
                            'reduction': f'{pct:.1f}%',
                            'status': '✅ 成功',
                            'dest': dest,
                        })
                    else:
                        results.append({
                            'filename': fname,
                            'orig': fmt_size(original_size),
                            'comp': '-', 'reduction': '-',
                            'status': f'❌ 失敗: {err or "不明なエラー"}',
                            'dest': '',
                        })
                except Exception as exc:
                    results.append({
                        'filename': fname,
                        'orig': '-', 'comp': '-', 'reduction': '-',
                        'status': f'❌ 失敗: {exc}',
                        'dest': '',
                    })
                finally:
                    if tmp_out and os.path.exists(tmp_out):
                        try:
                            os.unlink(tmp_out)
                        except OSError:
                            pass

            progress_bar.set_value(1.0)
            progress_label.set_text(
                f'完了 — {total} ファイル処理済み')

            with result_area:
                ui.separator()
                ui.label('処理結果').classes('font-bold text-gray-700 mt-2')
                cols = [
                    {'name': 'filename', 'label': 'ファイル名',
                     'field': 'filename', 'align': 'left'},
                    {'name': 'orig', 'label': '処理前',
                     'field': 'orig', 'align': 'right'},
                    {'name': 'comp', 'label': '処理後',
                     'field': 'comp', 'align': 'right'},
                    {'name': 'reduction', 'label': '削減率',
                     'field': 'reduction', 'align': 'right'},
                    {'name': 'status', 'label': '状態',
                     'field': 'status', 'align': 'center'},
                    {'name': 'dest', 'label': '出力先',
                     'field': 'dest', 'align': 'left'},
                ]
                ui.table(columns=cols, rows=results,
                         row_key='filename').classes('w-full text-sm')

            run_btn.enable()

        run_btn = ui.button(
            '圧縮開始', icon='compress',
            on_click=do_compress,
        ).classes('w-full text-lg py-3').props('color=primary')


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ in {'__main__', '__mp_main__'}:
    port = find_free_port(8080)
    ui.run(
        title='PDF圧縮ツール',
        port=port,
        reload=False,
        show=True,
        favicon='📄',
    )
