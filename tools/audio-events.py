#!/usr/bin/env python3
"""events.json（{t, kind, v} 列表）→ 音轨 → 与 silent 视频合并
用法: python audio-events.py <dir> [in.mp4] [out.mp4]
"""
import json, re, subprocess, sys, pathlib, os

D = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "out/swarm")
VIDEO = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else D / "film_silent.mp4")
OUT = pathlib.Path(sys.argv[3] if len(sys.argv) > 3 else D / "film_v.mp4")
ALIMIT = os.environ.get("ALIMIT", "0.66")
SFX_GAIN = float(os.environ.get("SFX_GAIN", "1"))
BGM_GAIN = float(os.environ.get("BGM_GAIN", "0.30"))
BGM_LP = os.environ.get("BGM_LP", "900")

SFX = pathlib.Path(r"D:\hermes-output\小红书诊断-20261113\claude-build\meme\assets\sfx")
BGM = pathlib.Path(r"D:\hermes-output\小红书诊断-20261113\claude-build\bgm\Deliberate_Thought.mp3")
MAP = {"pop": "pop.wav", "click": "click.wav", "boom": "boom.wav",
       "riser": "riser.wav", "tick": "click.wav"}

ev = json.loads((D / "events.json").read_text(encoding="utf-8"))
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(VIDEO)],
                           capture_output=True, text=True).stdout.strip())
print(f"video {dur:.2f}s, events {len(ev)}")

groups = {}
for e in ev:
    f = MAP.get(e["kind"].lstrip("e") if e["kind"].startswith("e") else e["kind"])
    if not f:
        continue
    vol = 0.09 if e["kind"].startswith("e") else 0.14
    if e["kind"].lstrip("e") == "pop":
        vol = 0.14 if e["kind"].startswith("e") else 0.20
    groups.setdefault(f, []).append((max(0.0, float(e["t"])), round(vol * SFX_GAIN, 4)))

args = ["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(BGM)]
order = sorted(groups)
for f in order:
    args += ["-i", str(SFX / f)]

filters = [f"[0:a]atrim=0:{dur},asetpts=N/SR/TB,volume={BGM_GAIN},lowpass=f={BGM_LP}[bg]"]
mixes = ["[bg]"]
for gi, f in enumerate(order):
    idx = gi + 1
    outs = []
    for k, (t, v) in enumerate(groups[f]):
        ms = int(t * 1000)
        filters.append(f"[{idx}:a]volume={v},adelay={ms}|{ms},aformat=channel_layouts=stereo[e{gi}_{k}]")
        outs.append(f"[e{gi}_{k}]")
    filters.append("".join(outs) + f"amix=inputs={len(outs)}:normalize=0:dropout_transition=0[g{gi}]")
    mixes.append(f"[g{gi}]")
filters.append("".join(mixes) + f"amix=inputs={len(mixes)}:normalize=0:dropout_transition=0[mixout]")

(D / "filter.txt").write_text(";".join(filters), encoding="utf-8")
args += ["-/filter_complex", str(D / "filter.txt"), "-map", "[mixout]", "-t", str(dur),
         "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(D / "mix.wav")]
r = subprocess.run(args, capture_output=True, text=True, errors="ignore")
if r.returncode:
    print(r.stderr[-700:]); raise SystemExit(1)

# 两遍 loudnorm（linear=true）：只做整体增益，不做动态压缩，
# 单遍动态模式会把 BGM/音效的配比压回去（实测改了增益几乎听不出差别）
import json as _json
_p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(D / "mix.wav"),
                     "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                    capture_output=True, text=True, errors="ignore")
_txt = _p.stderr[_p.stderr.rfind("{"):]
_txt = _txt[:_txt.rfind("}") + 1]
_m = _json.loads(_txt)
_ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={_m['input_i']}"
       f":measured_TP={_m['input_tp']}:measured_LRA={_m['input_lra']}"
       f":measured_thresh={_m['input_thresh']}:offset={_m['target_offset']}")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(D / "mix.wav"),
                "-af", f"{_ln},alimiter=limit={ALIMIT}:attack=3:release=80:level=0",
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(D / "mix_norm.wav")], check=True)

subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(VIDEO), "-i", str(D / "mix_norm.wav"),
                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", str(OUT)], check=True)

r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(OUT), "-af", "ebur128=peak=true", "-f", "null", "-"],
                   capture_output=True, text=True, errors="ignore")
I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
P = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
print(f"响度 {I[-1] if I else '?'} LUFS · 真峰值 {P[-1] if P else '?'} dBFS → {OUT}")
