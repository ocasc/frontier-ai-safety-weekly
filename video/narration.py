#!/usr/bin/env python3
"""Narration segments -> MiniMax TTS -> per-segment mp3 + timings.json + narration.wav.

Register: 新闻资讯型 (机器之心式报道体), per skill tts-narration-video:
emotion=neutral, speed 1.0, vol 0.9, pitch 0, sparse pause tags at idea boundaries.
Model/voice after A/B probe: speech-2.8-hd + female-chengshu (override below).
The spoken script comes from segments{SUF}.json (one [id, scene, text] row per segment);
no issue-specific text is hardcoded in this file.
"""
import json, os, pathlib, subprocess, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SUF = os.environ.get("SUF", "")              # e.g. "_fast" -> audio_fast/, timings_fast.json
SPEED = float(os.environ.get("SPEED", "1.0"))
OUT = ROOT / ("audio" + SUF)
OUT.mkdir(parents=True, exist_ok=True)

MODEL = "speech-2.8-hd"
VOICE = "female-chengshu"

SEG_FILE = ROOT / f"segments{SUF}.json"
if not SEG_FILE.exists():
    raise SystemExit(
        f"missing {SEG_FILE.name}: JSON list of [id, scene, spoken_text], one row per segment.\n"
        "scene names must match the scene keys used by render.html's renderAt(t).")
SEGMENTS = [tuple(x) for x in json.load(open(SEG_FILE, encoding="utf-8"))]

HEAD_PAD = 0.6     # silence before first word
SEG_GAP = 0.35     # silence between segments (scene transitions)
TAIL_PAD = 1.4     # silence after last word (end card holds)

def load_env():
    env = {}
    for line in open(os.path.expanduser("~/.hermes/.env")):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def synth(text, out):
    key = load_env()["MINIMAX_API_KEY"]
    body = {
        "model": MODEL, "text": text, "stream": False, "emotion": "neutral",
        "voice_setting": {"voice_id": VOICE, "speed": SPEED, "vol": 0.9, "pitch": 0},
        "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
    }
    req = urllib.request.Request(
        "https://api.minimax.io/v1/t2a_v2", data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read().decode())
    if d.get("base_resp", {}).get("status_code") != 0:
        raise RuntimeError(f"{out.name}: {d.get('base_resp')}")
    out.write_bytes(bytes.fromhex(d["data"]["audio"]))

def duration(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

def main():
    for sid, _, text in SEGMENTS:
        p = OUT / f"{sid}.mp3"
        if p.exists() and p.stat().st_size > 1000:
            print("skip", p.name)
            continue
        synth(text, p)
        print("OK", p.name)

    # timings: cumulative scene windows on the final timeline
    t = HEAD_PAD
    scenes = {}
    for sid, scene, _ in SEGMENTS:
        d = duration(OUT / f"{sid}.mp3")
        scenes[scene] = {"seg": sid, "start": round(t, 3), "end": round(t + d, 3), "dur": round(d, 3)}
        t += d + SEG_GAP
    total = t - SEG_GAP + TAIL_PAD
    json.dump({"head_pad": HEAD_PAD, "seg_gap": SEG_GAP, "tail_pad": TAIL_PAD,
               "total": round(total, 3), "scenes": scenes},
              open(ROOT / f"timings{SUF}.json", "w"), ensure_ascii=False, indent=1)
    print("timings:", json.dumps(scenes, ensure_ascii=False))
    print("total video seconds:", round(total, 2))

    # narration.wav: segments at their timeline offsets
    parts = []
    for i, (sid, _, _) in enumerate(SEGMENTS):
        off = int(round((HEAD_PAD + i * SEG_GAP + sum(
            duration(OUT / f"{s}.mp3") for s, _, _ in SEGMENTS[:i])) * 1000))
        parts += ["-i", str(OUT / f"{sid}.mp3")]
    n = len(SEGMENTS)
    fc = []
    for i, (sid, _, _) in enumerate(SEGMENTS):
        off = int(round((HEAD_PAD + i * SEG_GAP + sum(
            duration(OUT / f"{s}.mp3") for s, _, _ in SEGMENTS[:i])) * 1000))
        fc.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=mono,adelay={off}:all=1[d{i}]")
    fc.append("".join(f"[d{i}]" for i in range(n)) +
              f"amix=inputs={n}:normalize=0,apad,atrim=0:{total}[out]")
    subprocess.run(["ffmpeg", "-y", *parts, "-filter_complex", ";".join(fc),
                    "-map", "[out]", "-ar", "44100", "-ac", "1", str(ROOT / f"narration{SUF}.wav")],
                   check=True, capture_output=True)
    print(f"narration{SUF}.wav", round(duration(ROOT / f"narration{SUF}.wav"), 2), "s")

if __name__ == "__main__":
    main()
