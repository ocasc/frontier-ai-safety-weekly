#!/usr/bin/env python3
"""Deterministic render: video.html seek(t) -> PNG frames -> ffmpeg -> mux narration.

Usage:
  python3 render.py probe     # key frames only, for vision QA before the full run
  python3 render.py full      # every frame + mux narration.wav -> $OUT{SUF}.mp4 (OUT default video_out)
"""
import base64, json, os, pathlib, subprocess, sys, time

if len(sys.argv) < 2 or sys.argv[1] not in ("probe", "full"):
    raise SystemExit("usage: python3 render.py probe|full [suffix]   (suffix e.g. _v8)")

ROOT = pathlib.Path(__file__).resolve().parent
FPS = 30
SUF = sys.argv[2] if len(sys.argv) > 2 else ""     # e.g. "_fast"
FRAMES = ROOT / ("frames" + SUF)
PROBE = ROOT / ("probe" + SUF)
CFG = json.load(open(ROOT / f"timings{SUF}.json"))
TOTAL = CFG["total"]

def probe_times():                      # three probes per scene: start, mid, end
    ts = []
    for sc in CFG["scenes"].values():
        ts += [sc["start"] + 0.4, (sc["start"] + sc["end"]) / 2, sc["end"] - 0.4]
    return sorted(set(round(t, 2) for t in ts if 0.2 < t < TOTAL - 0.2))
PROBE_TIMES = probe_times()

def page():
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    b = pw.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    html = ROOT / f"video{SUF}.html"
    if not html.exists():
        html = ROOT / "video.html"
    pg.goto("file://" + str(html))
    beats_path = ROOT / f"beats{SUF}.json"
    if beats_path.exists():
        CFG["beats"] = json.load(open(beats_path))["beats"]
    pg.evaluate("cfg => { window.CFG = cfg; }", CFG)
    return pw, b, pg

def shot(pg, t):
    data_url = pg.evaluate(
        "t => { renderAt(t); return document.getElementById('cv').toDataURL('image/png'); }", t)
    return base64.b64decode(data_url.split(",", 1)[1])

def probe():
    PROBE.mkdir(exist_ok=True)
    pw, b, pg = page()
    for t in PROBE_TIMES:
        (PROBE / f"t{t:05.1f}.png").write_bytes(shot(pg, t))
        print("probe", t)
    b.close(); pw.stop()

def full():
    FRAMES = ROOT / ("frames" + SUF)
    FRAMES.mkdir(exist_ok=True)
    n = int(TOTAL * FPS) + 1
    existing = len(list(FRAMES.glob("f*.png")))
    if existing < n:
        pw, b, pg = page()
        t0 = time.time()
        for i in range(n):
            p = FRAMES / f"f{i:05d}.png"
            if p.exists():
                continue
            p.write_bytes(shot(pg, i / FPS))
            if i % 100 == 0:
                print(f"{i}/{n}  {time.time()-t0:.0f}s", flush=True)
        b.close(); pw.stop()
    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(FPS), "-i", str(FRAMES / "f%05d.png"),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        str(ROOT / f"silent{SUF}.mp4")], check=True, capture_output=True)
    out_mp4 = ROOT / f"{os.environ.get('OUT', 'video_out')}{SUF}.mp4"
    narr = ROOT / f"narration{SUF}.wav"
    bgm = ROOT / f"bgm_cut{SUF}.wav"
    if not bgm.exists():
        bgm = ROOT / "bgm_cut.wav"
    if bgm.exists():                     # voice + ducked BGM bed, loudnorm to -14 LUFS
        subprocess.run([
            "ffmpeg", "-y", "-i", str(ROOT / f"silent{SUF}.mp4"), "-i", str(narr), "-i", str(bgm),
            "-filter_complex",
            "[1:a]aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-1.5,asplit=2[voice][sc];"
            "[2:a]aformat=channel_layouts=stereo,volume=0.22,treble=g=-3:f=4000[bed];"
            "[bed][sc]sidechaincompress=threshold=0.05:ratio=16:attack=10:release=280[duck];"
            "[voice][duck]amix=inputs=2:normalize=0,alimiter=limit=0.89[aout]",
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", str(TOTAL), str(out_mp4)], check=True, capture_output=True)
    else:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(ROOT / f"silent{SUF}.mp4"), "-i", str(narr),
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-t", str(TOTAL), str(out_mp4)], check=True, capture_output=True)
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        str(out_mp4)], capture_output=True, text=True)
    print(out_mp4.name, r.stdout.strip(), "s")

if __name__ == "__main__":
    {"probe": probe, "full": full}[sys.argv[1]]()
