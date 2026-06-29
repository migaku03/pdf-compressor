import os
import subprocess
import tempfile
import shutil
import socket
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

UPLOAD_FOLDER = tempfile.mkdtemp()
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB


def find_ghostscript():
    candidates = [
        'gs', 'gswin64c', 'gswin32c',
        '/opt/homebrew/bin/gs',
        '/usr/local/bin/gs',
        '/usr/bin/gs',
    ]
    for cmd in candidates:
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def get_gs_settings(ratio):
    if ratio >= 0.9:
        return ['-dPDFSETTINGS=/printer']
    elif ratio >= 0.7:
        return ['-dPDFSETTINGS=/ebook']
    elif ratio >= 0.4:
        return ['-dPDFSETTINGS=/screen']
    else:
        return [
            '-dPDFSETTINGS=/screen',
            '-dColorImageResolution=72',
            '-dGrayImageResolution=72',
        ]


def compress_pdf(gs_cmd, input_path, output_path, ratio):
    gs_settings = get_gs_settings(ratio)
    cmd = [
        gs_cmd,
        '-sDEVICE=pdfwrite',
        '-dCompatibilityLevel=1.4',
        '-dNOPAUSE',
        '-dQUIET',
        '-dBATCH',
    ] + gs_settings + [
        f'-sOutputFile={output_path}',
        input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.returncode == 0, result.stderr


def format_size(size_bytes):
    if size_bytes >= 1024 * 1024:
        return f'{size_bytes / (1024 * 1024):.2f} MB'
    return f'{size_bytes / 1024:.1f} KB'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/check-gs')
def check_gs():
    gs_cmd = find_ghostscript()
    return jsonify({'available': gs_cmd is not None, 'command': gs_cmd})


@app.route('/compress', methods=['POST'])
def compress():
    gs_cmd = find_ghostscript()
    if not gs_cmd:
        return jsonify({
            'error': 'Ghostscriptが見つかりません。インストールしてください。'
        }), 500

    files = request.files.getlist('files')
    ratio = float(request.form.get('ratio', 0.5))
    overwrite = request.form.get('overwrite', 'false').lower() == 'true'
    original_paths = request.form.getlist('original_paths')

    if not files:
        return jsonify({'error': 'ファイルが選択されていません。'}), 400

    results = []

    for i, file in enumerate(files):
        if not file.filename.lower().endswith('.pdf'):
            continue

        original_path = original_paths[i] if i < len(original_paths) else file.filename
        filename = os.path.basename(original_path)

        tmp_input = None
        tmp_output = None

        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                tmp_input = f.name
                file.save(tmp_input)

            original_size = os.path.getsize(tmp_input)

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                tmp_output = f.name

            success, error_msg = compress_pdf(gs_cmd, tmp_input, tmp_output, ratio)

            if success and os.path.exists(tmp_output):
                compressed_size = os.path.getsize(tmp_output)
                reduction = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

                if overwrite:
                    dest_path = original_path
                else:
                    base, ext = os.path.splitext(original_path)
                    dest_path = base + '_SD' + ext

                shutil.copy2(tmp_output, dest_path)

                results.append({
                    'filename': filename,
                    'original_size': format_size(original_size),
                    'compressed_size': format_size(compressed_size),
                    'reduction': f'{reduction:.1f}%',
                    'output_path': dest_path,
                    'status': 'success',
                })
            else:
                results.append({
                    'filename': filename,
                    'original_size': format_size(original_size),
                    'compressed_size': '-',
                    'reduction': '-',
                    'output_path': '',
                    'status': 'error',
                    'error': error_msg or '圧縮に失敗しました。',
                })

        except Exception as e:
            results.append({
                'filename': filename,
                'original_size': '-',
                'compressed_size': '-',
                'reduction': '-',
                'output_path': '',
                'status': 'error',
                'error': str(e),
            })
        finally:
            for tmp in [tmp_input, tmp_output]:
                if tmp and os.path.exists(tmp):
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass

    return jsonify({'results': results})


def find_free_port(preferred=5000):
    for port in [preferred, preferred + 1]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    return preferred


if __name__ == '__main__':
    port = find_free_port(5000)
    print(f'Starting PDF Compressor on http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)
