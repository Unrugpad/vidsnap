from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp, os, uuid, threading, time
from gtts import gTTS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
DOWNLOAD_DIR = '/tmp/downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>VidSnap</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:Arial,sans-serif;background:#060810;color:#f1f5f9;}
.wrap{max-width:860px;margin:0 auto;padding:12px 14px 60px;}
nav{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;}
.logo{font-size:1.4rem;font-weight:900;color:#00e5ff;}.logo span{color:#f59e0b;}
.badge{font-size:0.65rem;background:rgba(0,229,255,0.1);border:1px solid rgba(0,229,255,0.3);color:#00e5ff;padding:3px 10px;border-radius:99px;}
h1{font-size:1.6rem;font-weight:900;text-align:center;margin-bottom:6px;line-height:1.2;}
h1 em{font-style:normal;color:#00e5ff;}
.sub{text-align:center;color:#64748b;font-size:0.82rem;margin-bottom:12px;}
.mwrap{overflow:hidden;margin-bottom:14px;}
.mq{display:flex;gap:8px;width:max-content;animation:scroll 20s linear infinite;}
@keyframes scroll{0%{transform:translateX(0);}100%{transform:translateX(-50%);}}
.chip{display:flex;align-items:center;gap:5px;padding:5px 11px;background:#111827;border:1px solid rgba(255,255,255,0.08);border-radius:99px;font-size:0.72rem;color:#94a3b8;white-space:nowrap;}
.tabs{display:flex;gap:4px;background:#0d1117;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:4px;margin-bottom:12px;}
.tab{flex:1;padding:12px;border:none;border-radius:8px;background:transparent;color:#64748b;font-weight:700;font-size:0.78rem;cursor:pointer;}
.tab.active{background:#111827;color:#f1f5f9;}
.panel{display:none;}.panel.active{display:block;}
.card{background:#111827;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:18px;}
.lbl{display:block;font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;color:#64748b;margin-bottom:7px;}
.row{display:flex;gap:8px;margin-bottom:12px;}
input[type=text],textarea,select{background:#0d1117;border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:10px 12px;color:#f1f5f9;font-size:0.88rem;font-family:Arial,sans-serif;outline:none;width:100%;}
textarea{resize:vertical;min-height:120px;}
.bfetch{background:linear-gradient(135deg,#00e5ff,#00b8d4);border:none;border-radius:8px;padding:10px 16px;font-weight:700;font-size:0.82rem;color:#000;cursor:pointer;white-space:nowrap;flex-shrink:0;}
.fgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:12px;}
.fopt{display:none;}
.flbl{display:flex;align-items:center;gap:6px;padding:8px 9px;background:#0d1117;border:1.5px solid rgba(255,255,255,0.08);border-radius:8px;cursor:pointer;font-size:0.72rem;font-weight:600;color:#94a3b8;}
.fopt:checked+.flbl{border-color:#00e5ff;color:#00e5ff;background:rgba(0,229,255,0.07);}
.prev{display:none;gap:10px;align-items:center;padding:10px;background:#0d1117;border:1px solid rgba(255,255,255,0.08);border-radius:8px;margin-bottom:12px;}
.prev.show{display:flex;}
.prev img{width:80px;height:52px;object-fit:cover;border-radius:6px;flex-shrink:0;}
.ptitle{font-size:0.8rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.pmeta{font-size:0.68rem;color:#64748b;}
.bdl{width:100%;padding:14px;border:none;border-radius:10px;background:linear-gradient(135deg,#7c3aed,#9333ea);color:#fff;font-weight:700;font-size:0.9rem;cursor:pointer;}
.btts{width:100%;padding:14px;border:none;border-radius:10px;background:linear-gradient(135deg,#f59e0b,#f97316);color:#000;font-weight:700;font-size:0.9rem;cursor:pointer;}
.bdl:disabled,.btts:disabled{opacity:0.5;}
.prog{display:none;margin-top:10px;}.prog.show{display:block;}
.pbar{height:3px;background:rgba(255,255,255,0.08);border-radius:99px;overflow:hidden;margin-bottom:6px;}
.pfill{height:100%;width:40%;background:linear-gradient(90deg,#00e5ff,#7c3aed);animation:sl 1.2s ease-in-out infinite;}
.pfill.tts{background:linear-gradient(90deg,#f59e0b,#f97316);}
@keyframes sl{0%{transform:translateX(-200%);}100%{transform:translateX(350%);}}
.ptxt{font-size:0.72rem;color:#64748b;text-align:center;}
.stt{display:none;padding:9px 12px;border-radius:8px;font-size:0.78rem;margin-top:10px;}
.stt.err{display:block;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.2);color:#fca5a5;}
.stt.ok{display:block;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.2);color:#6ee7b7;}
.crow{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;font-size:0.72rem;color:#64748b;}
.cbar{flex:1;height:3px;background:rgba(255,255,255,0.08);border-radius:99px;overflow:hidden;margin:0 10px;}
.cfill{height:100%;background:#10b981;transition:width 0.2s,background 0.2s;}
.topts{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;}
.slbl{font-size:0.68rem;text-transform:uppercase;color:#64748b;margin-bottom:5px;}
.afrow{display:flex;gap:6px;}
.afopt{display:none;}
.aflbl{flex:1;text-align:center;padding:9px;background:#0d1117;border:1.5px solid rgba(255,255,255,0.08);border-radius:8px;cursor:pointer;font-size:0.78rem;font-weight:700;color:#64748b;}
.afopt:checked+.aflbl{border-color:#f59e0b;color:#f59e0b;background:rgba(245,158,11,0.08);}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:18px;}
.stat{background:#111827;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px;text-align:center;}
.sn{font-size:1.6rem;font-weight:900;color:#00e5ff;}
.sl{font-size:0.65rem;color:#64748b;}
footer{text-align:center;margin-top:20px;font-size:0.7rem;color:#64748b;}
footer a{color:#00e5ff;text-decoration:none;}
</style>
</head>
<body>
<div class="wrap">
<nav><div class="logo">Vid<span>Snap</span></div><div class="badge">FREE</div></nav>
<h1>Download Videos &<br><em>Text to Audio</em></h1>
<p class="sub">1000+ platforms. Free forever.</p>
<div class="mwrap"><div class="mq">
<div class="chip">YouTube</div><div class="chip">TikTok</div><div class="chip">Instagram</div><div class="chip">Facebook</div><div class="chip">Twitter</div><div class="chip">Reddit</div><div class="chip">Vimeo</div><div class="chip">LinkedIn</div>
<div class="chip">YouTube</div><div class="chip">TikTok</div><div class="chip">Instagram</div><div class="chip">Facebook</div><div class="chip">Twitter</div><div class="chip">Reddit</div><div class="chip">Vimeo</div><div class="chip">LinkedIn</div>
</div></div>
<div class="tabs">
<button class="tab active" id="t1">Video Downloader</button>
<button class="tab" id="t2">Text to Audio</button>
</div>
<div id="pv" class="panel active"><div class="card">
<span class="lbl">Paste Video URL</span>
<div class="row">
<input type="text" id="ui" placeholder="Paste link here..."/>
<button class="bfetch" id="fb">Fetch</button>
</div>
<div class="prev" id="pb"><img id="pt" src="" alt=""/><div style="flex:1;min-width:0"><div class="ptitle" id="ptl"></div><div class="pmeta" id="pm"></div></div></div>
<span class="lbl">Choose Format</span>
<div class="fgrid">
<input type="radio" name="fmt" id="f1" value="mp4_hd" class="fopt" checked><label for="f1" class="flbl">MP4 HD</label>
<input type="radio" name="fmt" id="f2" value="mp4_sd" class="fopt"><label for="f2" class="flbl">MP4 SD</label>
<input type="radio" name="fmt" id="f3" value="3gp" class="fopt"><label for="f3" class="flbl">3GP</label>
<input type="radio" name="fmt" id="f4" value="mp3" class="fopt"><label for="f4" class="flbl">MP3</label>
<input type="radio" name="fmt" id="f5" value="m4a" class="fopt"><label for="f5" class="flbl">M4A</label>
<input type="radio" name="fmt" id="f6" value="webm" class="fopt"><label for="f6" class="flbl">WEBM</label>
</div>
<button class="bdl" id="db">Download</button>
<div class="prog" id="vp"><div class="pbar"><div class="pfill"></div></div><div class="ptxt">Processing... please wait</div></div>
<div class="stt" id="vs"></div>
</div></div>
<div id="pt2" class="panel"><div class="card">
<span class="lbl">Enter Text (max 3000 chars)</span>
<textarea id="tx" placeholder="Type or paste text here..."></textarea>
<div class="crow"><span id="ct">0 / 3000</span><div class="cbar"><div class="cfill" id="cf" style="width:0%"></div></div><span id="ch"></span></div>
<div class="topts">
<div><p class="slbl">Language</p>
<select id="tl"><option value="en">English</option><option value="fr">French</option><option value="es">Spanish</option><option value="de">German</option><option value="pt">Portuguese</option><option value="ar">Arabic</option><option value="hi">Hindi</option><option value="yo">Yoruba</option><option value="ha">Hausa</option></select></div>
<div><p class="slbl">Format</p><div class="afrow">
<input type="radio" name="af" id="a1" value="mp3" class="afopt" checked><label for="a1" class="aflbl">MP3</label>
<input type="radio" name="af" id="a2" value="wav" class="afopt"><label for="a2" class="aflbl">WAV</label>
</div></div></div>
<button class="btts" id="tb">Convert to Audio</button>
<div class="prog" id="tp"><div class="pbar"><div class="pfill tts"></div></div><div class="ptxt">Converting... please wait</div></div>
<div class="stt" id="ts"></div>
</div></div>
<div class="stats">
<div class="stat"><div class="sn">1000+</div><div class="sl">Platforms</div></div>
<div class="stat"><div class="sn">6</div><div class="sl">Formats</div></div>
<div class="stat"><div class="sn">Free</div><div class="sl">Forever</div></div>
</div>
<footer><p>VidSnap — Powered by yt-dlp & gTTS. Personal use only.</p></footer>
</div>
<script>
var MAX=3000;
var g=function(id){return document.getElementById(id);};
function showTab(t){
  g('t1').className=(t==='video')?'tab active':'tab';
  g('t2').className=(t==='tts')?'tab active':'tab';
  g('pv').className=(t==='video')?'panel active':'panel';
  g('pt2').className=(t==='tts')?'panel active':'panel';
}
function setStatus(id,type,msg){
  var e=g(id);
  e.className='stt '+(type==='error'?'err':'ok');
  e.textContent=(type==='error'?'\u2715 ':'\u2713 ')+msg;
}
function fmtDur(s){if(!s)return'';var m=Math.floor(s/60);var x=s%60;return m+':'+(x<10?'0':'')+x;}
function doFetch(){
  var url=g('ui').value.trim();
  if(!url){setStatus('vs','error','Please enter a URL.');return;}
  var btn=g('fb');btn.disabled=true;btn.textContent='...';
  g('vs').className='stt';
  fetch('/api/info',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url})})
  .then(function(r){return r.json().then(function(d){return{ok:r.ok,d:d};});})
  .then(function(res){
    if(!res.ok)throw new Error(res.d.error||'Failed');
    g('pt').src=res.d.thumbnail||'';
    g('ptl').textContent=res.d.title||'Untitled';
    g('pm').textContent=[res.d.uploader,fmtDur(res.d.duration)].filter(Boolean).join(' \u00b7 ');
    g('pb').className='prev show';
    setStatus('vs','ok','Video found! Choose format and download.');
  })
  .catch(function(e){setStatus('vs','error',e.message);})
  .then(function(){btn.disabled=false;btn.textContent='Fetch';});
}
function doDownload(){
  var url=g('ui').value.trim();
  if(!url){setStatus('vs','error','Please enter a URL.');return;}
  var fmt=document.querySelector('input[name="fmt"]:checked').value;
  var btn=g('db');btn.disabled=true;btn.textContent='Downloading...';
  g('vp').className='prog show';g('vs').className='stt';
  fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url,format:fmt})})
  .then(function(r){
    if(!r.ok)return r.json().then(function(d){throw new Error(d.error||'Failed');});
    var name='download';
    var disp=r.headers.get('Content-Disposition')||'';
    var m=disp.match(/filename[^;=\\n]*=((['"]).*?\\2|[^;\\n]*)/);
    if(m)name=decodeURIComponent(m[1].replace(/['"]/g,''));
    return r.blob().then(function(blob){return{blob:blob,name:name};});
  })
  .then(function(res){
    var a=document.createElement('a');a.href=URL.createObjectURL(res.blob);a.download=res.name;
    document.body.appendChild(a);a.click();document.body.removeChild(a);
    setStatus('vs','ok','Downloaded: '+res.name);
  })
  .catch(function(e){setStatus('vs','error',e.message);})
  .then(function(){g('vp').className='prog';btn.disabled=false;btn.textContent='Download';});
}
function doTTS(){
  var text=g('tx').value.trim();
  var lang=g('tl').value;
  var fmt=document.querySelector('input[name="af"]:checked').value;
  if(!text){setStatus('ts','error','Please enter some text.');return;}
  if(text.length>MAX){setStatus('ts','error','Text is over the 3000 limit.');return;}
  var btn=g('tb');btn.disabled=true;btn.textContent='Converting...';
  g('tp').className='prog show';g('ts').className='stt';
  fetch('/api/tts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text,lang:lang,format:fmt})})
  .then(function(r){
    if(!r.ok)return r.json().then(function(d){throw new Error(d.error||'Failed');});
    return r.blob();
  })
  .then(function(blob){
    var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='audio.'+fmt;
    document.body.appendChild(a);a.click();document.body.removeChild(a);
    setStatus('ts','ok','Audio downloaded!');
  })
  .catch(function(e){setStatus('ts','error',e.message);})
  .then(function(){g('tp').className='prog';btn.disabled=false;btn.textContent='Convert to Audio';});
}
function updateChar(){
  var l=g('tx').value.length;
  var p=Math.min(l/MAX*100,100);
  g('ct').textContent=l+' / '+MAX;
  var f=g('cf');f.style.width=p+'%';
  f.style.background=l>MAX?'#ef4444':(l>2500?'#f59e0b':'#10b981');
  g('ch').textContent=l>MAX?'Over!':(l>2500?(MAX-l)+' left':'');
}
g('t1').addEventListener('click',function(){showTab('video');});
g('t2').addEventListener('click',function(){showTab('tts');});
g('fb').addEventListener('click',doFetch);
g('db').addEventListener('click',doDownload);
g('tb').addEventListener('click',doTTS);
g('tx').addEventListener('input',updateChar);
g('ui').addEventListener('keydown',function(e){if(e.key==='Enter')doFetch();});
</script>
</body>
</html>"""

def cleanup_file(path, delay=300):
    def _delete():
        time.sleep(delay)
        try:
            if os.path.exists(path): os.remove(path)
        except: pass
    threading.Thread(target=_delete, daemon=True).start()

@app.route('/')
def index():
    return HTML

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/info', methods=['POST','OPTIONS'])
def get_info():
    if request.method == 'OPTIONS': return '',200
    try:
        data = request.get_json(force=True)
        url = data.get('url','').strip()
        if not url: return jsonify({'error':'No URL'}),400
        with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'skip_download':True,'socket_timeout':30}) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({'title':info.get('title',''),'thumbnail':info.get('thumbnail',''),'duration':info.get('duration',0),'uploader':info.get('uploader',''),'platform':info.get('extractor_key','')})
    except Exception as e: return jsonify({'error':str(e)}),400

@app.route('/api/download', methods=['POST','OPTIONS'])
def download_video():
    if request.method == 'OPTIONS': return '',200
    try:
        data = request.get_json(force=True)
        url = data.get('url','').strip()
        fmt = data.get('format','mp4_hd')
        if not url: return jsonify({'error':'No URL'}),400
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
        opts = {'format':cfg['format'],'outtmpl':os.path.join(DOWNLOAD_DIR,file_id+'.%(ext)s'),'quiet':True,'socket_timeout':60}
        if 'merge_output_format' in cfg: opts['merge_output_format'] = cfg['merge_output_format']
        if 'postprocessors' in cfg: opts['postprocessors'] = cfg['postprocessors']
        with yt_dlp.YoutubeDL(opts) as ydl: info = ydl.extract_info(url, download=True)
        downloaded = None
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(file_id):
                downloaded = os.path.join(DOWNLOAD_DIR,f); break
        if not downloaded: return jsonify({'error':'Download failed'}),500
        title = info.get('title','video')
        safe = "".join(c for c in title if c.isalnum() or c in(' ','-','_')).strip()
        ext = downloaded.rsplit('.',1)[-1]
        cleanup_file(downloaded)
        return send_file(downloaded, as_attachment=True, download_name=safe+'.'+ext)
    except Exception as e: return jsonify({'error':str(e)}),400

@app.route('/api/tts', methods=['POST','OPTIONS'])
def tts():
    if request.method == 'OPTIONS': return '',200
    try:
        data = request.get_json(force=True)
        text = data.get('text','').strip()
        lang = data.get('lang','en')
        fmt = data.get('format','mp3')
        if not text: return jsonify({'error':'No text'}),400
        if len(text) > 3000: return jsonify({'error':'Text too long'}),400
        file_id = str(uuid.uuid4())
        mp3 = os.path.join(DOWNLOAD_DIR,file_id+'.mp3')
        wav = os.path.join(DOWNLOAD_DIR,file_id+'.wav')
        gTTS(text=text,lang=lang,slow=False).save(mp3)
        if fmt=='wav':
            os.system('ffmpeg -y -i "'+mp3+'" "'+wav+'" -loglevel quiet')
            cleanup_file(mp3,10); cleanup_file(wav)
            return send_file(wav,as_attachment=True,download_name='audio.wav')
        cleanup_file(mp3)
        return send_file(mp3,as_attachment=True,download_name='audio.mp3')
    except Exception as e: return jsonify({'error':str(e)}),400

if __name__ == '__main__':
    port = int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0',port=port,debug=False)
