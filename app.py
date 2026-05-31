from flask import Flask, request, jsonify, send_file, render_template_from_string
from flask_cors import CORS
import yt_dlp
import os
import uuid
import threading
import time
from gtts import gTTS

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

DOWNLOAD_DIR = '/tmp/downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup_file(path, delay=300):
    def _delete():
        time.sleep(delay)
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass
    threading.Thread(target=_delete, daemon=True).start()

@app.route('/')
def index():
    with open('templates/index.html', 'r') as f:
        return f.read()

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', ''),
                'platform': info.get('extractor_key', ''),
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url', '').strip()
    fmt = data.get('format', 'mp4_hd')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    file_id = str(uuid.uuid4())

    format_configs = {
        'mp4_hd': {
            'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[ext=mp4]/best',
            'ext': 'mp4',
            'label': 'MP4 HD',
            'merge_output_format': 'mp4',
        },
        'mp4_sd': {
            'format': 'bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480][ext=mp4]/best[height<=480]',
            'ext': 'mp4',
            'label': 'MP4 SD',
            'merge_output_format': 'mp4',
        },
        '3gp': {
            'format': 'best[ext=3gp]/worst[ext=mp4]/worst',
            'ext': '3gp',
            'label': '3GP',
        },
        'mp3': {
            'format': 'bestaudio/best',
            'ext': 'mp3',
            'label': 'MP3 Audio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        },
        'm4a': {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'ext': 'm4a',
            'label': 'M4A Audio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }],
        },
        'webm': {
            'format': 'bestvideo[ext=webm]+bestaudio[ext=webm]/bestvideo[ext=webm]+bestaudio/best[ext=webm]/best',
            'ext': 'webm',
            'label': 'WEBM',
            'merge_output_format': 'webm',
        },
    }

    config = format_configs.get(fmt, format_configs['mp4_hd'])
    out_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    ydl_opts = {
        'format': config['format'],
        'outtmpl': out_path,
        'quiet': True,
        'no_warnings': True,
    }

    if 'merge_output_format' in config:
        ydl_opts['merge_output_format'] = config['merge_output_format']

    if 'postprocessors' in config:
        ydl_opts['postprocessors'] = config['postprocessors']

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')

        # Find the downloaded file
        downloaded = None
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(file_id):
                downloaded = os.path.join(DOWNLOAD_DIR, f)
                break

        if not downloaded:
            return jsonify({'error': 'Download failed'}), 500

        ext = downloaded.rsplit('.', 1)[-1]
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        download_name = f"{safe_title}.{ext}"

        cleanup_file(downloaded)

        return send_file(
            downloaded,
            as_attachment=True,
            download_name=download_name
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 400


MAX_TTS_CHARS = 3000

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    data = request.json
    text = data.get('text', '').strip()
    lang = data.get('lang', 'en')
    fmt = data.get('format', 'mp3')  # mp3 or wav

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    if len(text) > MAX_TTS_CHARS:
        return jsonify({'error': f'Text exceeds {MAX_TTS_CHARS} character limit'}), 400

    file_id = str(uuid.uuid4())
    mp3_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp3")
    wav_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.wav")

    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(mp3_path)

        if fmt == 'wav':
            os.system(f'ffmpeg -y -i "{mp3_path}" "{wav_path}" -loglevel quiet')
            cleanup_file(mp3_path, delay=10)
            cleanup_file(wav_path)
            return send_file(wav_path, as_attachment=True, download_name='audio.wav', mimetype='audio/wav')
        else:
            cleanup_file(mp3_path)
            return send_file(mp3_path, as_attachment=True, download_name='audio.mp3', mimetype='audio/mpeg')

    except Exception as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
