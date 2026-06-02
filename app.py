from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import yt_dlp, os, uuid, threading, time, json, asyncio
import urllib.request
import edge_tts

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
DOWNLOAD_DIR = '/tmp/downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Token contract addresses
UPAD_CA = "JuLhhMjaWyWKCWEPetMV5hucpCmR212MzrRLWWZEgem"
BNC_CA = "0x591DF09AF60366298FE31C4590a9230585D34FBd"

# Edge-TTS voices: male and female per language
VOICES = {
    "en":      {"male": "en-US-GuyNeural",      "female": "en-US-AriaNeural"},
    "en-GB":   {"male": "en-GB-RyanNeural",     "female": "en-GB-SoniaNeural"},
    "en-NG":   {"male": "en-NG-AbeoNeural",     "female": "en-NG-EzinneNeural"},
    "fr":      {"male": "fr-FR-HenriNeural",    "female": "fr-FR-DeniseNeural"},
    "es":      {"male": "es-ES-AlvaroNeural",   "female": "es-ES-ElviraNeural"},
    "de":      {"male": "de-DE-ConradNeural",   "female": "de-DE-KatjaNeural"},
    "pt":      {"male": "pt-BR-AntonioNeural",  "female": "pt-BR-FranciscaNeural"},
    "ar":      {"male": "ar-SA-HamedNeural",    "female": "ar-SA-ZariyahNeural"},
    "hi":      {"male": "hi-IN-MadhurNeural",   "female": "hi-IN-SwaraNeural"},
}

with open('index.html', encoding='utf-8') as _f:
    HTML = _f.read()

def cleanup_file(path, delay=300):
    def _delete():
        time.sleep(delay)
        try:
            if os.path.exists(path): os.remove(path)
        except: pass
    threading.Thread(target=_delete, daemon=True).start()

FRIENDLY_ERR = ("This video could not be fetched right now. The platform may be "
    "temporarily blocking automated requests. Please try again in a moment, or try "
    "a link from TikTok, Instagram, Facebook, Twitter or another supported platform.")

def make_ydl_opts(extra):
    # Base options with browser impersonation + YouTube client switching
    opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        # Switch YouTube player clients: android & ios bypass many web blocks
        'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web', 'tv']}},
    }
    # Try to add Chrome browser impersonation (curl_cffi) to beat TLS fingerprinting.
    # Wrapped safely so a yt-dlp version without this API never breaks the request.
    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget
        opts['impersonate'] = ImpersonateTarget('chrome')
    except Exception:
        pass
    opts.update(extra)
    return opts

@app.route('/')
def index():
    return HTML

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/prices')
def prices():
    def fetch_token(chain, ca):
        try:
            url = "https://api.dexscreener.com/latest/dex/tokens/" + ca
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            pairs = data.get('pairs') or []
            if not pairs:
                return None
            # pick the pair with highest liquidity
            best = max(pairs, key=lambda p: (p.get('liquidity') or {}).get('usd', 0) or 0)
            return {
                'price': best.get('priceUsd'),
                'change': (best.get('priceChange') or {}).get('h24')
            }
        except Exception:
            return None
    upad = fetch_token('solana', UPAD_CA)
    bnc = fetch_token('bsc', BNC_CA)
    return jsonify({'upad': upad, 'bnc': bnc})

@app.route('/api/info', methods=['POST','OPTIONS'])
def get_info():
    if request.method == 'OPTIONS': return '',200
    try:
        data = request.get_json(force=True)
        url = data.get('url','').strip()
        if not url: return jsonify({'error':'Please enter a URL.'}),400
        try:
            with yt_dlp.YoutubeDL(make_ydl_opts({'skip_download':True})) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception:
            # fallback: plain options without impersonation
            with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'skip_download':True,'socket_timeout':30}) as ydl:
                info = ydl.extract_info(url, download=False)
        return jsonify({'title':info.get('title',''),'thumbnail':info.get('thumbnail',''),'duration':info.get('duration',0),'uploader':info.get('uploader',''),'platform':info.get('extractor_key','')})
    except Exception:
        return jsonify({'error': FRIENDLY_ERR}),400

@app.route('/api/download', methods=['POST','OPTIONS'])
def download_video():
    if request.method == 'OPTIONS': return '',200
    try:
        data = request.get_json(force=True)
        url = data.get('url','').strip()
        fmt = data.get('format','mp4_hd')
        if not url: return jsonify({'error':'Please enter a URL.'}),400
        file_id = str(uuid.uuid4())
        configs = {
            'mp4_hd':{'format':'best[ext=mp4][height<=1080]/bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best','merge_output_format':'mp4'},
            'mp4_sd':{'format':'best[ext=mp4][height<=480]/best[height<=480]/best','merge_output_format':'mp4'},
            '3gp':{'format':'best[ext=3gp]/worst[ext=mp4]/worst'},
            'mp3':{'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}]},
            'm4a':{'format':'bestaudio[ext=m4a]/bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'m4a','preferredquality':'192'}]},
            'webm':{'format':'best[ext=webm]/bestvideo[ext=webm]+bestaudio[ext=webm]/best','merge_output_format':'webm'},
        }
        cfg = configs.get(fmt, configs['mp4_hd'])
        extra = {'format':cfg['format'],'outtmpl':os.path.join(DOWNLOAD_DIR,file_id+'.%(ext)s')}
        if 'merge_output_format' in cfg: extra['merge_output_format'] = cfg['merge_output_format']
        if 'postprocessors' in cfg: extra['postprocessors'] = cfg['postprocessors']
        try:
            with yt_dlp.YoutubeDL(make_ydl_opts(extra)) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception:
            # fallback without impersonation
            extra2 = dict(extra); extra2.update({'quiet':True,'no_warnings':True,'socket_timeout':60})
            with yt_dlp.YoutubeDL(extra2) as ydl:
                info = ydl.extract_info(url, download=True)
        downloaded = None
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(file_id):
                downloaded = os.path.join(DOWNLOAD_DIR,f); break
        if not downloaded: return jsonify({'error':FRIENDLY_ERR}),500
        title = info.get('title','video')
        safe = "".join(c for c in title if c.isalnum() or c in(' ','-','_')).strip() or 'video'
        ext = downloaded.rsplit('.',1)[-1]
        cleanup_file(downloaded)
        return send_file(downloaded, as_attachment=True, download_name=safe+'.'+ext)
    except Exception:
        return jsonify({'error':FRIENDLY_ERR}),400

def run_edge_tts(text, voice, out_path):
    async def _gen():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(out_path)
    asyncio.run(_gen())

@app.route('/api/tts', methods=['POST','OPTIONS'])
def tts():
    if request.method == 'OPTIONS': return '',200
    try:
        data = request.get_json(force=True)
        text = data.get('text','').strip()
        lang = data.get('lang','en')
        fmt = data.get('format','mp3')
        voice_gender = data.get('voice','male')
        if not text: return jsonify({'error':'Please enter some text.'}),400
        if len(text) > 3000: return jsonify({'error':'Text is over the 3000 character limit.'}),400
        voice = VOICES.get(lang, VOICES['en']).get(voice_gender, VOICES['en']['male'])
        file_id = str(uuid.uuid4())
        mp3 = os.path.join(DOWNLOAD_DIR,file_id+'.mp3')
        wav = os.path.join(DOWNLOAD_DIR,file_id+'.wav')
        run_edge_tts(text, voice, mp3)
        if fmt=='wav':
            os.system('ffmpeg -y -i "'+mp3+'" "'+wav+'" -loglevel quiet')
            cleanup_file(mp3,10); cleanup_file(wav)
            return send_file(wav,as_attachment=True,download_name='audio.wav')
        cleanup_file(mp3)
        return send_file(mp3,as_attachment=True,download_name='audio.mp3')
    except Exception as e:
        return jsonify({'error':'Audio conversion failed. Please try again.'}),400

if __name__ == '__main__':
    port = int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0',port=port,debug=False)
