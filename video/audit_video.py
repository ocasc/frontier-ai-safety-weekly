#!/usr/bin/env python3
"""Automated bug audit of a rendered cut: layout band violations, stalls, blank frames, audio gaps."""
import json, os, pathlib, subprocess, sys
import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
if len(sys.argv) < 2:
    raise SystemExit("usage: python3 audit_video.py <cut.mp4> [timings-suffix]   (suffix e.g. _v8)")
VIDEO = ROOT / sys.argv[1] if not os.path.isabs(sys.argv[1]) else pathlib.Path(sys.argv[1])
SUF = sys.argv[2] if len(sys.argv) > 2 else ""
TMP = ROOT / "_audit_frames"
TMP.mkdir(exist_ok=True)
TIM = json.load(open(ROOT / f"timings{SUF}.json"))
TOTAL = TIM["total"]

# 1) sample frames at 3 fps
if not list(TMP.glob("f*.png")):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(VIDEO), "-vf", "fps=3",
                    str(TMP / "f%04d.png")], check=True)
files = sorted(TMP.glob("f*.png"))
print(f"sampled {len(files)} frames at 3fps from {VIDEO.name}")

def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.int16)

issues = []
ink_hist = []
prev = None
stalls = []
blank = 0
for i, p in enumerate(files):
    t = i / 3.0
    im = load(p)
    ink = (im.sum(axis=2) < 730)           # any non-white pixel
    ink_hist.append(int(ink.sum()))
    if ink.sum() < 200:
        blank += 1
    # a) frame-edge ink (ignore progress bar 1068-1080 and cut sweep 0-9)
    body = ink[10:1066, :]
    left, right = body[:, :4].sum(), body[:, -4:].sum()
    top = ink[10:14, :].sum()               # 4 rows just under the cut sweep
    if left > 40 or right > 40:
        issues.append(f"t={t:5.2f} ink at side edge (L={left} R={right})")
    if top > 40:
        issues.append(f"t={t:5.2f} ink just under top edge ({top})")
    # b) reserved bottom bands must stay empty
    if ink[985:1021, :].sum() > 60:
        issues.append(f"t={t:5.2f} ink inside reserved gap 985-1020 ({int(ink[985:1021,:].sum())})")
    if ink[1056:1068, :].sum() > 60:
        issues.append(f"t={t:5.2f} ink between subtitle and bar ({int(ink[1056:1068,:].sum())})")
    # c) subtitle must be present (after the first 0.4s of each scene it should be drawn)
    sub = ink[1022:1056, :].sum()
    if t > 1.5 and sub < 300:
        issues.append(f"t={t:5.2f} subtitle band empty ({int(sub)} px)")
    # d) stall detection: identical consecutive sampled frames
    if prev is not None and np.array_equal(prev, im):
        stalls.append(round(t, 2))
    prev = im

# 2) scene-window sanity: every scene must contain changing pixels
print("\n-- scene coverage --")
for name, sc in TIM["scenes"].items():
    idx = [i for i in range(len(files)) if sc["start"] + 0.35 <= i / 3.0 <= sc["end"] - 0.1]
    if not idx:
        issues.append(f"scene {name} too short to sample")
        continue
    ims = [load(files[i]) for i in idx]
    diffs = [float(np.abs(ims[k + 1] - ims[k]).mean()) for k in range(len(ims) - 1)]
    moving = sum(1 for d in diffs if d > 0.05)
    print(f"{name:9} {sc['start']:6.2f}-{sc['end']:6.2f}s  frames={len(idx):3}  moving={moving:3}/{max(1,len(diffs))}")
    if moving < max(1, len(diffs)) * 0.6:
        issues.append(f"scene {name} looks static ({moving}/{len(diffs)} frame pairs changed)")

# 3) audio: gaps, clicks, clipping
print("\n-- audio --")
r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(VIDEO), "-ac", "1", "-ar", "16000",
                    "-f", "f32le", "-"], capture_output=True)
x = np.frombuffer(r.stdout, dtype=np.float32)
sr = 16000
hop = 160
env = np.array([np.sqrt((x[i:i + hop] ** 2).mean()) for i in range(0, len(x) - hop, hop)])
db = 20 * np.log10(env + 1e-12)
print(f"len={len(x)/sr:.2f}s  peak={np.abs(x).max():.3f}  mean RMS={db.mean():.1f} dB")
if np.abs(x).max() > 0.999:
    issues.append("audio clipping (peak >= 1.0)")
# silence holes inside speech windows (>0.25s below -45dB)
for name, sc in TIM["scenes"].items():
    a, b = int(sc["start"] * sr / hop) + 4, int(sc["end"] * sr / hop) - 4
    seg = db[a:b]
    holes, run = [], 0
    for v in seg:
        run = run + 1 if v < -45 else 0
        holes.append(run)
    worst = max(holes) if holes else 0
    if worst * hop / sr > 0.25:
        issues.append(f"silence hole {worst*hop/sr:.2f}s inside scene {name}")
    print(f"{name:9} speech RMS {seg.mean():6.1f} dB  worst hole {worst*hop/sr:.2f}s")
# 4) music-only gaps
for name, sc in TIM["scenes"].items():
    pass
print("\n-- stalls --", stalls[:10], "total", len(stalls))
print("-- blank frames --", blank)
print("\n-- ISSUES --")
print("\n".join(issues) if issues else "none found")
