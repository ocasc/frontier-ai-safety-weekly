#!/usr/bin/env python3
"""BGM prep: beat grid + trimmed bed covering the whole cut (SUF selects timings).

Track: bgm/<BGM>.mp3, default "mixkit_134" (Mixkit Stock Music Free License,
commercial use allowed). Pick a track whose bed survives under speech. Dark centroid (1036Hz) so it sits under the voice.
Outputs bgm_cut.wav (exactly TOTAL seconds, fades) + beats.json (beat times).
"""
import json, os, pathlib, subprocess
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "bgm" / (os.environ.get("BGM", "mixkit_134") + ".mp3")
SUF = os.environ.get("SUF", "")
TOTAL = json.load(open(ROOT / f"timings{SUF}.json"))["total"]
SR = 22050

def pcm(p, sr=SR):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(sr),
                        "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.float32).copy(), sr

x, sr = pcm(SRC)
hop, win = 512, 1024
frames = np.stack([x[i*hop:i*hop+win] for i in range((len(x)-win)//hop)])
mag = np.abs(np.fft.rfft(frames*np.hanning(win), axis=1))
flux = np.maximum(0, np.diff(mag, axis=0)).sum(1)
flux = (flux - flux.mean()) / (flux.std() + 1e-9)
fps = sr / hop

# tempo by autocorrelation, then phase by pulse-train fit
ac = np.correlate(flux, flux, 'full')[len(flux)-1:]
lags = np.arange(1, int(1.2 * fps))
bpms = 60.0 * fps / lags
ac_lags = ac[1:1 + len(lags)]
mask = (bpms > 100) & (bpms < 150)
period = lags[mask][np.argmax(ac_lags[mask])]
beat = period / fps                                  # seconds per beat
bpm = 60.0 / beat
grid = np.arange(0, flux.size / fps, beat)
best_phase, best_score = 0.0, -1e9
for phase in np.arange(0, beat, beat / 40):
    pts = ((grid + phase) * fps).astype(int)
    pts = pts[pts < flux.size]
    score = flux[pts].sum()
    if score > best_score:
        best_score, best_phase = score, phase
beats = [round(float(t + best_phase), 3) for t in np.arange(0, TOTAL + beat, beat)]
if bpm < 80:                                   # sparse/slow bed: subdivide to 8th notes for hit points
    sub = [round(float(t + best_phase - beat / 2), 3) for t in np.arange(0, TOTAL + beat, beat)]
    beats = sorted(set(beats + [b for b in sub if b >= 0]))
    print("subdivided to 8ths ->", len(beats), "hit points")
print(f"bpm={bpm:.2f} beat={beat:.4f}s phase={best_phase:.3f}s beats={len(beats)}")

# trimmed bed: same length as the video, gentle fades.
# Short sources are crossfade-looped, so the bed never ends mid-video
# (mixkit_565 is 295s and a 412s cut silently lost its music past 295s otherwise).
def src_dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

D = src_dur(SRC)
XF = 3.0
if D >= TOTAL:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(SRC),
                    "-t", str(TOTAL), "-af",
                    f"afade=t=in:st=0:d=1.2,afade=t=out:st={TOTAL-2.5}:d=2.5,alimiter=limit=0.9",
                    "-ar", "44100", "-ac", "2", str(ROOT / f"bgm_cut{SUF}.wav")], check=True)
else:
    b_len = TOTAL - D + XF
    fc = (f"[0:a]atrim=0:{D},asetpts=PTS-STARTPTS[a];"
          f"[1:a]atrim=0:{b_len},asetpts=PTS-STARTPTS[b];"
          f"[a][b]acrossfade=d={XF}:c1=tri:c2=tri[m];"
          f"[m]afade=t=in:st=0:d=1.2,afade=t=out:st={TOTAL-2.5}:d=2.5,alimiter=limit=0.9[out]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(SRC), "-i", str(SRC),
                    "-filter_complex", fc, "-map", "[out]", "-t", str(TOTAL),
                    "-ar", "44100", "-ac", "2", str(ROOT / f"bgm_cut{SUF}.wav")], check=True)
    print(f"bed crossfade-looped: src {D:.1f}s -> {TOTAL:.1f}s")
json.dump({"bpm": round(bpm, 2), "beat": round(beat, 4), "beats": beats},
          open(ROOT / f"beats{SUF}.json", "w"), indent=1)
print(f"bgm_cut{SUF}.wav + beats{SUF}.json written, total", TOTAL)
