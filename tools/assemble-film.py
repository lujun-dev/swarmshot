#!/usr/bin/env python3
"""assemble-film.py — 两幕 → 套真机外壳 → 裁开头 → 转场 → 音效 → 成片（一条命令）

用法:
  python assemble-film.py --a1 out/act1m --a2 out/act2f --out out/SwarmShot-v12-real.mp4

做的事:
  1) 用 out/real/shellA.png 给第一幕套真机外壳（内容 1480x833 贴 220,142）
  2) 两幕各裁掉开头 TRIM 秒（引擎入场）
  3) xfade 偏移 = 第一幕最后一处 press 时刻 - TRIM + TAIL（默认 0.45）
  4) sfx.json → events.json（place|key→pop, press→click）→ audio-events.py 混音出片
缓存: out/r1_<a1名>.mp4 / out/r1t_<a1名>.mp4 / out/r2t_<a2名>.mp4，签名一致就复用
"""
import argparse, json, subprocess, sys, pathlib, hashlib, os

ROOT = pathlib.Path(__file__).resolve().parent
SHELL_A = ROOT / "out/real/shellA.png"
SHELL_B = ROOT / "out/real/shellB.png"
TRIM = 2.30
XFADE = 0.35
TAIL = 0.45


def run(args, quiet=True):
    r = subprocess.run(args, capture_output=True, text=True, errors="ignore")
    if r.returncode:
        print(" ".join(str(a) for a in args)[:400])
        print((r.stderr or "")[-1200:])
        raise SystemExit(1)
    if not quiet and r.stdout:
        print(r.stdout.strip())
    return r


def dur(p):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(p)])
    return float(r.stdout.strip())


def sig(p):
    st = pathlib.Path(p).stat()
    return f"{st.st_size}-{int(st.st_mtime)}"


def shell(src, shell_png, dst, label):
    if dst.exists() and dst.stat().st_size > 0:
        side = dst.with_suffix(".sig")
        if side.exists() and side.read_text() == sig(src) + sig(shell_png):
            print(f"[cache] {dst.name}")
            return
    print(f"[shell] {label} → {dst.name}")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-loop", "1", "-i", str(shell_png),
         "-filter_complex",
         "[0:v]scale=1480:833,setsar=1[c];[1:v][c]overlay=220:142:shortest=1,"
         "noise=alls=4:allf=t,format=yuv420p",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", "30", str(dst)])
    dst.with_suffix(".sig").write_text(sig(src) + sig(shell_png))


def trimmed(src, dst, tail=0.0):
    tag = f"-{TRIM}+{tail}"
    if dst.exists() and dst.stat().st_size > 0:
        side = dst.with_suffix(".sig")
        if side.exists() and side.read_text() == sig(src) + tag:
            print(f"[cache] {dst.name}")
            return
    args = ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(TRIM), "-i", str(src)]
    if tail > 0:
        args += ["-t", f"{dur(src) - tail - TRIM:.3f}"]   # -ss 在前时 -to 的基准不可靠，用 -t
    args += ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", str(dst)]
    print(f"[trim] {tag}s → {dst.name}")
    run(args)
    dst.with_suffix(".sig").write_text(sig(src) + tag)


def build_events(a1, a2, offset, out_json):
    drop = set(os.environ.get("SFX_DROP", "key").split(","))   # 默认丢掉打字音效
    ev = []
    for d, shift in ((a1, -TRIM), (a2, -TRIM + offset)):
        for e in json.loads((d / "sfx.json").read_text(encoding="utf-8")):
            if e["fn"] in drop:
                continue
            kind = {"place": "pop", "key": "pop", "press": "click"}.get(e["fn"])
            if not kind:
                continue
            t = e["t"] + shift
            if t < 0:
                continue
            ev.append({"t": round(t, 3), "kind": kind,
                       "v": 0.9 if kind == "click" else 0.45})
    ev.sort(key=lambda x: x["t"])
    out_json.write_text(json.dumps(ev), encoding="utf-8")
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a1", required=True)
    ap.add_argument("--a2", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--xfade", type=float, default=None, help="覆盖自动算出的转场偏移")
    ap.add_argument("--sfx", type=float, default=0.80, help="音效整体增益")
    ap.add_argument("--bgm", type=float, default=0.30, help="BGM 增益")
    ap.add_argument("--bgmlp", type=int, default=900, help="BGM 低通截止 Hz（越大越亮）")
    ap.add_argument("--a2tail", type=float, default=0.0, help="第二幕末尾裁掉几秒（收尾太长时用）")
    a = ap.parse_args()
    a1, a2 = ROOT / a.a1, ROOT / a.a2
    out = ROOT / a.out
    work = out.parent / out.stem.replace("SwarmShot-", "film-")
    work.mkdir(parents=True, exist_ok=True)

    tag1, tag2 = a1.name, a2.name
    r1, r1t = ROOT / f"out/r1_{tag1}.mp4", ROOT / f"out/r1t_{tag1}.mp4"
    r2t = ROOT / f"out/r2t_{tag2}.mp4"
    shell(a1 / "silent.mp4", SHELL_A, r1, "act1")
    shell(a2 / "silent.mp4", SHELL_B, ROOT / f"out/r2_{tag2}.mp4", "act2")
    trimmed(r1, r1t)
    trimmed(ROOT / f"out/r2_{tag2}.mp4", r2t, a.a2tail)

    presses = [e["t"] for e in json.loads((a1 / "sfx.json").read_text(encoding="utf-8"))
               if e["fn"] == "press"]
    offset = a.xfade if a.xfade is not None else round(presses[-1] - TRIM + TAIL, 3)
    print(f"[xfade] offset {offset}s  (last press {presses[-1]:.2f})")

    silent = work / "silent.mp4"
    max_off = min(dur(r1t), dur(r2t)) - XFADE - 0.2
    if offset > max_off:
        offset = max_off
        print(f"[xfade] clamped to {offset:.2f}")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(r1t), "-i", str(r2t),
         "-filter_complex",
         f"[0:v][1:v]xfade=transition=fade:duration={XFADE}:offset={offset},format=yuv420p",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", "30", str(silent)])

    ev = build_events(a1, a2, offset, work / "events.json")
    print(f"[audio] {len(ev)} events")
    import os
    os.environ["SFX_GAIN"] = str(a.sfx)
    os.environ["BGM_GAIN"] = str(a.bgm)
    os.environ["BGM_LP"] = str(a.bgmlp)
    print(f"[audio] sfx gain {a.sfx}  bgm gain {a.bgm}  bgm lp {a.bgmlp}Hz")
    run([sys.executable, str(ROOT / "audio-events.py"), str(work), str(silent), str(out)], quiet=False)
    print(f"[done] {out}  {dur(out):.2f}s  {out.stat().st_size/1e6:.1f}MB")


if __name__ == "__main__":
    main()
