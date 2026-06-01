from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp, os, uuid, threading, time
from gtts import gTTS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

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
    return send_file('templates/index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/info', methods=['POST', 'OPTIONS'])
def get_info():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json(force=True)
        url = data.get('url', '').strip()
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'socket_timeout': 30,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', ''),
                'platform': info.get('extractor_key', '')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/download', methods=['POST', 'OPTIONS'])
def download_video():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json(force=True)
        url = data.get('url', '').strip()
        fmt = data.get('format', 'mp4_hd')
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        file_id = str(uuid.uuid4())
        configs = {
            'mp4_hd': {'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio/best', 'merge_output_format': 'mp4'},
            'mp4_sd': {'format': 'bestvideo[ext=mp4][height<=480]+bestaudio/best', 'merge_output_format': 'mp4'},
            '3gp': {'format': 'best[ext=3gp]/worst'},
            'mp3': {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]},
            'm4a': {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a', 'preferredquality': '192'}]},
            'webm': {'format': 'bestvideo[ext=webm]+bestaudio/best', 'merge_output_format': 'webm'},
        }
        cfg = configs.get(fmt, configs['mp4_hd'])
        opts = {
            'format': cfg['format'],
            'outtmpl': os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s"),
            'quiet': True,
            'socket_timeout': 60,
        }
        if 'merge_output_format' in cfg:
            opts['merge_output_format'] = cfg['merge_output_format']
        if 'postprocessors' in cfg:
            opts['postprocessors'] = cfg['postprocessors']
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        downloaded = next((os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) if f.startswith(file_id)), None)
        if not downloaded:
            return jsonify({'error': 'Download failed - file not found'}), 500
        title = info.get('title', 'video')
        safe = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        ext = downloaded.rsplit('.', 1)[-1]
        cleanup_file(downloaded)
        return send_file(downloaded, as_attachment=True, download_name=f"{safe}.{ext}")
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/tts', methods=['POST', 'OPTIONS'])
def tts():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json(force=True)
        text = data.get('text', '').strip()
        lang = data.get('lang', 'en')
        fmt = data.get('format', 'mp3')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        if len(text) > 3000:
            return jsonify({'error': 'Text exceeds 3000 character limit'}), 400
        file_id = str(uuid.uuid4())
        mp3 = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp3")
        wav = os.path.join(DOWNLOAD_DIR, f"{file_id}.wav")
        gTTS(text=text, lang=lang, slow=False).save(mp3)
        if fmt == 'wav':
            os.system(f'ffmpeg -y -i "{mp3}" "{wav}" -loglevel quiet')
            cleanup_file(mp3, 10)
            cleanup_file(wav)
            return send_file(wav, as_attachment=True, download_name='audio.wav')
        cleanup_file(mp3)
        return send_file(mp3, as_attachment=True, download_name='audio.mp3')
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
