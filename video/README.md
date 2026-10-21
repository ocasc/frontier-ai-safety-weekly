# Narrated explainer video (optional)

Turns one card's script into a narrated 1080p motion-graphics cut: HTML canvas
animated by `renderAt(t)`, rendered frame by frame in a headless browser,
muxed with MiniMax TTS narration and a ducked music bed. No video model, no
timeline editor, and every frame is reproducible from the script.

```
segments.json ──► narration.py ──► narration.wav + timings.json + audio/*.mp3
                                        │
                     bgm.py ────────────┤► bgm_cut.wav + beats.json
                                        │
                     render.py ─────────┴► $OUT.mp4   (frames + mux + duck)
                     audit_video.py ─────► pass/fail bug audit of the cut
```

## Files in an issue's `video/` directory

| File | Role |
|---|---|
| `segments.json` (or `segments_SUF.json`) | the script: `[[id, scene, spoken_text], ...]`; `<#0.4#>` pause tags allowed |
| `video.html` (or `video_SUF.html`) | one HTML file drawing the film; must expose `renderAt(t)` and a `#cv` canvas at 1920x1080 |
| `bgm/<stem>.mp3` | music bed; `BGM=<stem>` selects it (default `mixkit_134`) |
| `narration.py` | MiniMax `t2a_v2` per segment -> `audio/`, then `timings{SUF}.json` + `narration{SUF}.wav` |
| `bgm.py` | beat grid by autocorrelation, bed trimmed to the exact cut length, crossfade-looped when the track is shorter |
| `render.py` | `probe` (key frames for vision QA) or `full` (every frame, ffmpeg encode, sidechain-ducked mix) |
| `audit_video.py` | samples the cut at 3 fps and flags layout-band violations, stalled scenes, blank frames and audio gaps |

## Run

```bash
cd <issue>/video
export SUF=_v8              # variant suffix, empty by default
export OUT=card3_explainer  # output name, default video_out
python3 narration.py        # needs MINIMAX_API_KEY in ~/.hermes/.env
python3 bgm.py              # needs BGM=<stem> and bgm/<stem>.mp3
python3 render.py probe     # QA a few frames before paying for the full render
python3 render.py full
python3 audit_video.py card3_explainer_v8.mp4 _v8
```

`timings{SUF}.json` is the single source of truth for timing: narration writes
it, `bgm.py` and `render.py` both read it, `audit_video.py` needs it to know
where scene boundaries are. Changing the script means re-running narration
before anything else.

## Requirements

`ffmpeg`/`ffprobe` on PATH, Google Chrome (or `CHROME_BIN`), and
`pip install -r ../requirements.txt` (playwright, numpy, Pillow).

## Design rules that the scripts cannot enforce

- Subtitles are one line per time slice (<= 56 CJK chars, split on punctuation).
  Two-line blocks intrude on the bottom reserved band.
- Camera pushes stay at or below 1.025; faster reads as a zoom, not a push.
- At a scene seam, keep the outgoing frame until the hard cut. Dispatch by the
  scene that has **started**, not the one that has not ended, or the incoming
  scene's elements peek into the seam.
- Voice over music by 9 to 14 dB, and always verify the audio bed covers the
  whole cut: a track shorter than the video silently loses its music late in
  the cut, which `audit_video.py` then reports as a silence hole.

## Scope

These are the scripts used for the weekly's card explainers, mirrored here so
they can be reused. The live chain runs inside an issue's `video/` directory
together with the content (scripts, narration text, audio), which is not
published in this repository. `prompt_animation.md` is the model-facing brief
that produced the original animation and is the fastest way to get a new
`video.html`.
