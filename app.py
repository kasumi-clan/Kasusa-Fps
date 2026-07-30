import os, uuid, threading, subprocess, re, time
from flask import Flask, request, jsonify, Response, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE, "uploads")
OUTPUT_DIR = os.path.join(BASE, "outputs")
LOG_DIR = os.path.join(BASE, "logs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
FFMPEG_TIMEOUT = 600

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = None

JOBS = {}
RES_MAP = {"original": None, "1080p": "1080", "2k": "1440", "4k": "2160"}
LAG_MAP = {"light": "12", "medium": "6", "heavy": "3"}

HTML_PAGE = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kasusa Method</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
:root{ --neon:#38e8ff; --neon2:#a78bfa; --ink:#15151a;
  --rainbow: linear-gradient(90deg,#ff3b30,#ff9500,#ffcc00,#34c759,#00c7be,#5856d6,#af52de); }
body{ margin:0; min-height:100vh; overflow-x:hidden; background:#07070a; color:#fff; font-family:'Poppins',system-ui,sans-serif; display:flex; align-items:center; justify-content:center; padding:24px; position:relative; }
.bg-blob{ position:fixed; border-radius:50%; filter:blur(70px); opacity:.28; z-index:0; will-change:transform; animation:float 14s ease-in-out infinite; }
.b1{ width:260px; height:260px; background:var(--neon); top:-50px; left:-50px; }
.b2{ width:300px; height:300px; background:var(--neon2); bottom:-70px; right:-50px; animation-delay:4s; }
@keyframes float{ 0%,100%{ transform:translate3d(0,0,0) scale(1);} 50%{ transform:translate3d(15px,-20px,0) scale(1.1);} }
.wrap{ position:relative; z-index:1; width:100%; max-width:460px; background:linear-gradient(180deg,rgba(255,255,255,.97),rgba(232,233,238,.97)); backdrop-filter:blur(16px); border:1px solid rgba(255,255,255,.5); border-radius:24px; padding:32px 26px; color:var(--ink); box-shadow:0 25px 60px rgba(0,0,0,.55), 0 0 50px -18px var(--neon); animation:cardIn .5s cubic-bezier(.2,.85,.3,1.2); }
@keyframes cardIn{ from{ opacity:0; transform:translateY(16px) scale(.97);} to{ opacity:1; transform:translateY(0) scale(1);} }
.top-row{ display:flex; align-items:center; justify-content:space-between; margin-bottom:2px; }
h1{ font-weight:800; font-size:24px; margin:0; letter-spacing:.2px; color:#4b4b55; }
h1 span{ background:var(--rainbow); background-size:200% auto; -webkit-background-clip:text; background-clip:text; color:transparent; animation:hueMove 6s linear infinite; }
@keyframes hueMove{ to{ background-position:200% center; } }
#musicBtn{ width:38px; height:38px; border-radius:50%; border:1px solid rgba(0,0,0,.1); background:#fff; font-size:16px; cursor:pointer; display:flex; align-items:center; justify-content:center; transition:.2s; box-shadow:0 4px 10px rgba(0,0,0,.08); }
#musicBtn:active{ transform:scale(.88); }
#musicBtn.on{ background:linear-gradient(180deg,var(--neon),#0891b2); color:#fff; box-shadow:0 0 16px -2px var(--neon); }
.sub{ color:#6b6b76; font-size:12.5px; margin:2px 0 24px; font-weight:500; }
.drop{ display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; gap:6px; border:2px dashed rgba(0,0,0,.14); border-radius:16px; padding:26px 16px; cursor:pointer; color:#4a4a54; font-size:14px; outline:none; user-select:none; transition:.2s; background:rgba(0,0,0,.02); }
.drop:hover, .drop:focus{ border-color:#0891b2; color:#111; background:rgba(56,232,255,.06); }
#previewBox{ margin-top:14px; border-radius:14px; overflow:hidden; animation:popIn .4s cubic-bezier(.2,.9,.3,1.3); }
#previewVideo{ width:100%; display:block; max-height:210px; background:#000; border-radius:14px; }
.row{ display:flex; gap:12px; margin:20px 0; }
.field{ flex:1; display:flex; flex-direction:column; gap:6px; }
.field label{ font-size:11px; color:#7a7a84; text-transform:uppercase; letter-spacing:.5px; font-weight:600; }
select{ background:#fff; color:var(--ink); border:1px solid rgba(0,0,0,.12); border-radius:10px; padding:11px 12px; font-family:inherit; font-size:13.5px; outline:none; transition:.2s; }
select:focus{ border-color:#0891b2; box-shadow:0 0 0 3px rgba(56,232,255,.18); }
button#submitBtn{ width:100%; padding:15px; border:none; border-radius:14px; background:linear-gradient(180deg,#1c1c22,#000); color:#fff; font-family:inherit; font-weight:700; font-size:15px; cursor:pointer; outline:none; transition:.15s; box-shadow:0 10px 24px -8px rgba(0,0,0,.5); }
button#submitBtn:hover{ box-shadow:0 10px 28px -6px rgba(56,232,255,.5); }
button#submitBtn:active{ transform:scale(.96); }
button#submitBtn:disabled{ background:#c9c9d0; color:#8a8a90; cursor:not-allowed; box-shadow:none; }
.progress-wrap{ margin-top:22px; animation:popIn .4s cubic-bezier(.2,.9,.3,1.3); }
#statusText{ font-size:12.5px; color:#55555f; margin:0 0 8px; text-align:center; font-weight:500; }
.progress-bar{ position:relative; width:100%; height:24px; background:#e7e7ec; border:1px solid rgba(0,0,0,.06); border-radius:999px; overflow:hidden; }
.progress-fill{ height:100%; width:0%; background:var(--rainbow); background-size:300% 100%; animation:hueMove 3s linear infinite; box-shadow:0 0 16px -2px rgba(0,0,0,.25); transition:width .35s ease; position:relative; overflow:hidden; }
.progress-fill::after{ content:''; position:absolute; inset:0; background-image:linear-gradient(45deg,rgba(255,255,255,.28) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.28) 50%,rgba(255,255,255,.28) 75%,transparent 75%,transparent); background-size:26px 26px; animation:stripes 1s linear infinite; }
@keyframes stripes{ from{ background-position:0 0;} to{ background-position:26px 0;} }
.progress-label{ position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-size:11.5px; font-weight:700; color:#0d0d10; text-shadow:0 1px 2px rgba(255,255,255,.7); }
.download-btn{ display:block; text-align:center; margin-top:20px; padding:15px; background:linear-gradient(180deg,#ffffff,#e4e5ea); color:var(--ink); border:1px solid rgba(0,0,0,.08); border-radius:14px; text-decoration:none; font-weight:700; opacity:0; transform:translateY(16px) scale(.9); animation:popIn .55s cubic-bezier(.2,.9,.25,1.4) forwards; box-shadow:0 12px 28px -8px rgba(56,232,255,.4); }
.download-btn:active{ transform:scale(.96); }
@keyframes popIn{ from{ opacity:0; transform:translateY(16px) scale(.9);} to{ opacity:1; transform:translateY(0) scale(1); } }
.error{ color:#d6294a; text-align:center; margin-top:16px; font-size:12.5px; font-weight:500; animation:popIn .3s ease; }
.hint{ font-size:11px; color:#9a9aa3; text-align:center; margin-top:10px; }
.hidden{ display:none !important; }
</style></head>
<body>
<div class="bg-blob b1"></div><div class="bg-blob b2"></div>
<div class="wrap">
  <div class="top-row">
    <h1>🎛️ Kasusa <span>Method</span></h1>
    <button type="button" id="musicBtn" title="Nhạc chill">🔇</button>
  </div>
  <p class="sub">Tăng Fps Với Chất Lượng Video Miễn Phí!</p>
  <form id="form">
    <label class="drop" id="dropLabel" for="fileInput">
      <span id="fileText">📁 Chọn video từ máy</span>
      <input type="file" id="fileInput" name="video" accept="video/*" hidden>
    </label>
    <div id="previewBox" class="hidden"><video id="previewVideo" controls muted></video></div>
    <div class="row">
      <div class="field"><label>FPS đầu ra</label>
        <select id="fps" name="fps">
          <option value="30">30 FPS</option>
          <option value="60" selected>60 FPS</option>
          <option value="120">120 FPS</option>
          <option value="144">144 FPS</option>
        </select></div>
      <div class="field"><label>Độ phân giải</label>
        <select id="resolution" name="resolution">
          <option value="original">Giữ nguyên</option>
          <option value="1080p" selected>1080p</option>
          <option value="2k">2K</option>
          <option value="4k">4K</option>
        </select></div>
    </div>
    <div class="row" style="margin-bottom:20px">
      <div class="field"><label>Hiệu ứng</label>
        <select id="motion" name="motion">
          <option value="lag" selected>🐢 Lag</option>
          <option value="smooth">✨ Siêu mượt</option>
        </select></div>
      <div class="field"><label>Cường độ Lag</label>
        <select id="intensity" name="intensity">
          <option value="light">Nhẹ</option>
          <option value="medium" selected>Vừa</option>
          <option value="heavy">Mạnh</option>
        </select></div>
    </div>
    <button type="submit" id="submitBtn">🚀 Xử lý video</button>
    <p class="hint">Đợi tí! Nâng Fps Với Chất Lượng Sắp Xong Rồi!</p>
  </form>
  <div id="progressWrap" class="progress-wrap hidden">
    <p id="statusText">Đang xử lý...</p>
    <div class="progress-bar">
      <div class="progress-fill" id="progressFill"></div>
      <span class="progress-label" id="progressLabel">0%</span>
    </div>
  </div>
  <a id="downloadBtn" class="download-btn hidden" href="#">⬇️ Tải video kết quả</a>
  <p id="errorText" class="error hidden"></p>
</div>
<script>
const form=document.getElementById('form'),fileInput=document.getElementById('fileInput'),fileText=document.getElementById('fileText'),submitBtn=document.getElementById('submitBtn'),progressWrap=document.getElementById('progressWrap'),progressFill=document.getElementById('progressFill'),progressLabel=document.getElementById('progressLabel'),statusText=document.getElementById('statusText'),downloadBtn=document.getElementById('downloadBtn'),errorText=document.getElementById('errorText'),previewBox=document.getElementById('previewBox'),previewVideo=document.getElementById('previewVideo'),musicBtn=document.getElementById('musicBtn');

let actx=null, musicOn=false, chordTimer=null;
const CHORDS=[[440,554.37,659.25],[392,493.88,587.33],[349.23,440,523.25],[392,493.88,587.33]];
function ensureContext(){
  if(!actx) actx=new (window.AudioContext||window.webkitAudioContext)();
  return actx.resume();
}
function startMusic(){
  const master=actx.createGain(); master.gain.value=0.28; master.connect(actx.destination);
  const filter=actx.createBiquadFilter(); filter.type='lowpass'; filter.frequency.value=1200; filter.connect(master);
  let i=0;
  function playChord(freqs){
    freqs.forEach(f=>{
      const o=actx.createOscillator(); o.type='sine'; o.frequency.value=f;
      const g=actx.createGain(); g.gain.value=0; o.connect(g); g.connect(filter);
      o.start();
      g.gain.linearRampToValueAtTime(0.4,actx.currentTime+1.0);
      g.gain.linearRampToValueAtTime(0,actx.currentTime+3.4);
      o.stop(actx.currentTime+3.6);
    });
  }
  playChord(CHORDS[0]);
  chordTimer=setInterval(()=>{ i=(i+1)%CHORDS.length; playChord(CHORDS[i]); },3400);
}
function stopMusic(){
  if(chordTimer){ clearInterval(chordTimer); chordTimer=null; }
  if(actx) actx.suspend();
}
musicBtn.addEventListener('click', async ()=>{
  musicOn=!musicOn;
  musicBtn.classList.toggle('on',musicOn);
  musicBtn.textContent=musicOn?'🔊':'🔇';
  if(musicOn){
    await ensureContext();
    if(!chordTimer) startMusic();
  } else {
    stopMusic();
  }
});

async function wakeServer(maxMs){
  const start=Date.now();
  while(Date.now()-start < maxMs){
    try{
      const ctrl=new AbortController();
      const t=setTimeout(()=>ctrl.abort(), 6000);
      const r=await fetch('/', {signal:ctrl.signal, cache:'no-store'});
      clearTimeout(t);
      if(r.ok) return true;
    }catch(e){}
    await new Promise(res=>setTimeout(res,2000));
  }
  return false;
}

fileInput.addEventListener('change',()=>{
  const f=fileInput.files[0];
  if(f){
    fileText.textContent='✅ '+f.name;
    previewVideo.src=URL.createObjectURL(f);
    previewBox.classList.remove('hidden');
  }
});
form.addEventListener('submit', async (e)=>{
  e.preventDefault(); errorText.classList.add('hidden'); downloadBtn.classList.add('hidden');
  if(!fileInput.files[0]){ showError('Vui lòng chọn một video trước.'); return; }
  submitBtn.disabled=true; progressWrap.classList.remove('hidden'); setProgress(0);
  statusText.textContent='Đang đánh thức server... (có thể mất tới 60 giây)';
  const awake = await wakeServer(70000);
  if(!awake){ showError('Server chưa phản hồi, đợi 1-2 phút rồi thử lại nhé.'); resetBtn(); return; }
  statusText.textContent='Đang tải file lên...';
  const fd=new FormData();
  fd.append('video',fileInput.files[0]);
  fd.append('fps',document.getElementById('fps').value);
  fd.append('resolution',document.getElementById('resolution').value);
  fd.append('motion',document.getElementById('motion').value);
  fd.append('intensity',document.getElementById('intensity').value);
  try{
    const res=await fetch('/upload',{method:'POST',body:fd}); const data=await res.json();
    if(data.error){ showError(data.error); resetBtn(); return; }
    statusText.textContent='Đang xử lý video...'; pollProgress(data.job_id);
  }catch(err){ showError('Lỗi kết nối tới server.'); resetBtn(); }
});
function pollProgress(jobId){
  const timer=setInterval(async ()=>{
    try{
      const res=await fetch('/progress/'+jobId); const data=await res.json();
      if(data.error){ clearInterval(timer); showError(data.error); resetBtn(); return; }
      setProgress(data.percent||0);
      if(data.done){
        clearInterval(timer);
        if(data.file){
          statusText.textContent='Hoàn tất! 🎉'; setProgress(100);
          downloadBtn.href='/download/'+jobId;
          downloadBtn.classList.remove('hidden');
          downloadBtn.style.animation='none'; void downloadBtn.offsetWidth; downloadBtn.style.animation='';
        } else { showError('Xử lý thất bại, vui lòng thử lại.'); }
        resetBtn();
      }
    }catch(err){ clearInterval(timer); showError('Mất kết nối trong khi xử lý.'); resetBtn(); }
  },700);
}
function setProgress(p){ progressFill.style.width=p+'%'; progressLabel.textContent=p+'%'; }
function showError(msg){ errorText.textContent='⚠️ '+msg; errorText.classList.remove('hidden'); }
function resetBtn(){ submitBtn.disabled=false; }
</script>
</body></html>"""


def get_duration(path):
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path
        ]).decode().strip()
        return float(out)
    except Exception:
        return 0.0


def build_filter(height, fps, motion, intensity):
    parts = []
    if height:
        parts.append(f"scale=-2:{height}:flags=lanczos")
    if motion == "smooth":
        parts.append(f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:vsbmc=1")
    else:
        step = LAG_MAP.get(intensity, "6")
        parts.append(f"fps={step}")
        parts.append(f"fps={fps}")
    return ",".join(parts)


def process_video(job_id, in_path, out_path, fps, height, motion, intensity):
    duration = get_duration(in_path)
    vf = build_filter(height, fps, motion, intensity)
    cmd = ["ffmpeg", "-y", "-i", in_path, "-vf", vf,
           "-crf", "20", "-preset", "veryfast", "-c:v", "libx264",
           "-c:a", "aac", "-progress", "pipe:1", out_path]
    log_path = os.path.join(LOG_DIR, job_id + ".log")
    try:
        with open(log_path, "w") as errlog:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errlog, text=True)
            start = time.time()
            for line in proc.stdout:
                if time.time() - start > FFMPEG_TIMEOUT:
                    proc.kill()
                    JOBS[job_id].update(error="Xử lý quá lâu (quá {}s) - có thể server đang thiếu tài nguyên. Thử video ngắn/nhẹ hơn.".format(FFMPEG_TIMEOUT), done=True)
                    return
                m = re.search(r"out_time_ms=(\d+)", line)
                if m and duration > 0:
                    ms = int(m.group(1))
                    JOBS[job_id]["percent"] = min(99, int((ms / 1000000) / duration * 100))
                if "progress=end" in line:
                    JOBS[job_id]["percent"] = 100
            proc.wait(timeout=30)
        if proc.returncode == 0 and os.path.exists(out_path):
            JOBS[job_id].update(percent=100, done=True, file=os.path.basename(out_path))
        else:
            tail = ""
            try:
                with open(log_path, "r", errors="ignore") as f:
                    tail = f.read()[-350:]
            except Exception:
                pass
            JOBS[job_id].update(error="ffmpeg lỗi (mã {}): {}".format(proc.returncode, tail or "không rõ nguyên nhân"), done=True)
    except Exception as e:
        JOBS[job_id].update(error="Lỗi hệ thống: " + str(e), done=True)
    finally:
        if os.path.exists(in_path):
            os.remove(in_path)
        if os.path.exists(log_path):
            os.remove(log_path)


@app.route("/")
def index():
    return Response(HTML_PAGE, mimetype="text/html")


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("video")
    fps = request.form.get("fps", "60")
    resolution = request.form.get("resolution", "1080p")
    motion = request.form.get("motion", "lag")
    intensity = request.form.get("intensity", "medium")
    if not f or f.filename == "":
        return jsonify({"error": "Chưa chọn file video"}), 400
    job_id = uuid.uuid4().hex
    ext_in = os.path.splitext(f.filename)[1] or ".mp4"
    in_path = os.path.join(UPLOAD_DIR, job_id + ext_in)
    out_path = os.path.join(OUTPUT_DIR, job_id + ".mp4")
    f.save(in_path)
    height = RES_MAP.get(resolution, "1080")
    JOBS[job_id] = {"percent": 0, "done": False, "error": None, "file": None}
    threading.Thread(target=process_video, args=(job_id, in_path, out_path, fps, height, motion, intensity), daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/progress/<job_id>")
def progress(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Không tìm thấy job"}), 404
    return jsonify(job)


@app.route("/download/<job_id>")
def download(job_id):
    job = JOBS.get(job_id)
    if not job or not job.get("file"):
        return jsonify({"error": "File chưa sẵn sàng"}), 404
    return send_from_directory(OUTPUT_DIR, job["file"], as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, threaded=True)