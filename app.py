from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp, os, uuid, threading, time
from gtts import gTTS

app = Flask(__name__)
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
    return send_file('templates/index.html')

@app.route('/api/info', methods=['POST'])
def get_info():
    url = request.json.get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL'}), 400
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title', ''),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', ''),
                'platform': info.get('extractor_key', '')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/download', methods=['POST'])
def download_video():
    url = request.json.get('url', '').strip()
    fmt = request.json.get('format', 'mp4_hd')
    if not url:
        return jsonify({'error': 'No URL'}), 400
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
        'quiet': True
    }
    if 'merge_output_format' in cfg:
        opts['merge_output_format'] = cfg['merge_output_format']
    if 'postprocessors' in cfg:
        opts['postprocessors'] = cfg['postprocessors']
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        downloaded = next((os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) if f.startswith(file_id)), None)
        if not downloaded:
            return jsonify({'error': 'Download failed'}), 500
        title = info.get('title', 'video')
        safe = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        cleanup_file(downloaded)
        return send_file(downloaded, as_attachment=True, download_name=f"{safe}.{downloaded.rsplit('.', 1)[-1]}")
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/tts', methods=['POST'])
def tts():
    text = request.json.get('text', '').strip()
    lang = request.json.get('lang', 'en')
    fmt = request.json.get('format', 'mp3')
    if not text:
        return jsonify({'error': 'No text'}), 400
    if len(text) > 3000:
        return jsonify({'error': 'Too long'}), 400
    file_id = str(uuid.uuid4())
    mp3 = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp3")
    wav = os.path.join(DOWNLOAD_DIR, f"{file_id}.wav")
    try:
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
