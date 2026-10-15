#!/usr/bin/env python3
"""
Talking-head video editor: measure, edit, verify.

Subcommands
  probe    full diagnostic — dimensions, rotation, loudness, band energies,
           pause map, clipping. ALWAYS run this before editing.
  grid     write a coordinate-gridded still so you can read off crop numbers
  render   the actual edit (pauses, audio, grade, aspect, encode)
  contact  contact sheet of N frames, for verifying a finished render

Everything is measured rather than assumed. The defaults are deliberately
conservative: the common failure here is over-processing footage that was
already fine.
"""
import argparse, json, math, re, subprocess, sys
from pathlib import Path

# ── encode profile that plays everywhere ───────────────────
# Main@4.0 with no B-frames. B-frames produce negative DTS at the start, which
# is legal but which some macOS players and social uploaders refuse.
COMPAT = ["-profile:v", "main", "-level", "4.0", "-bf", "0",
          "-g", "60", "-keyint_min", "30",
          "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
          "-video_track_timescale", "30000", "-avoid_negative_ts", "make_zero",
          "-movflags", "+faststart", "-map_metadata", "-1"]

# full repair chain — only for genuinely damaged audio (wind, rumble, very quiet)
AUDIO_REPAIR = ("highpass=f=95:poles=2,highpass=f=95:poles=2,"
                "afftdn=nr=12:nf=-25,"
                "equalizer=f=250:t=q:w=1.2:g=-2,"
                "equalizer=f=3000:t=q:w=1.0:g=2.5,"
                "acompressor=threshold=-20dB:ratio=3:attack=15:release=200:makeup=2")

GRADE_LIGHT = "eq=contrast=1.06:saturation=1.10:gamma=1.02,unsharp=5:5:0.35:5:5:0.0"


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def die(m):
    sys.exit(f"error: {m}")


# ── probing ────────────────────────────────────────────────

def rotation(v):
    o = sh(["ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream_side_data=rotation",
            "-show_entries", "stream_tags=rotate",
            "-of", "default=noprint_wrappers=1:nokey=1", str(v)]).stdout
    for tok in o.split():
        try:
            return int(float(tok)) % 360
        except ValueError:
            pass
    return 0


def info(v):
    """Displayed dimensions (rotation applied), fps, duration, audio presence."""
    o = sh(["ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(v)]).stdout.split()
    if len(o) < 4:
        die(f"could not probe {v}")
    w, h = int(o[0]), int(o[1])
    num, den = (o[2].split("/") + ["1"])[:2]
    fps = float(num) / float(den or 1)
    dur = float(o[3])
    rot = rotation(v)
    if rot in (90, 270):
        w, h = h, w
    has_a = "audio" in sh(["ffprobe", "-v", "error", "-select_streams", "a:0",
                           "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                           str(v)]).stdout
    return dict(w=w, h=h, fps=fps, dur=dur, rot=rot, audio=has_a)


def band(v, f):
    o = sh(["ffmpeg", "-hide_banner", "-i", str(v), "-vn", "-af",
            f"{f},volumedetect", "-f", "null", "/dev/null"]).stderr
    m = re.search(r"mean_volume: (-?[0-9.]+) dB", o)
    return float(m.group(1)) if m else None


def loudness(v, extra=""):
    af = (extra + "," if extra else "") + "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json"
    o = sh(["ffmpeg", "-hide_banner", "-i", str(v), "-vn", "-af", af,
            "-f", "null", "/dev/null"]).stderr
    m = re.search(r"\{[^{}]*\"input_i\".*?\}", o, re.S)
    if not m:
        die("loudnorm measurement failed")
    return json.loads(m.group(0))


def pauses(v, noise="-28dB", mind=0.30):
    o = sh(["ffmpeg", "-hide_banner", "-i", str(v), "-vn", "-af",
            f"silencedetect=noise={noise}:d={mind}", "-f", "null", "/dev/null"]).stderr
    s = [float(x) for x in re.findall(r"silence_start: (-?[0-9.]+)", o)]
    e = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", o)]
    return [(max(0.0, a), b) for a, b in zip(s, e)]


def cmd_probe(a):
    v = Path(a.video).expanduser().resolve()
    i = info(v)
    print(f"{v.name}")
    print(f"  {i['w']}x{i['h']} displayed  ({'rotated ' + str(i['rot']) + '°' if i['rot'] else 'no rotation'})"
          f"  {i['fps']:.2f}fps  {i['dur']:.2f}s  audio={'yes' if i['audio'] else 'NO'}")
    if not i["audio"]:
        print("  !! no audio stream — players and uploaders often reject this")
        return
    ln = loudness(v)
    tgt = float(ln["input_i"])
    if not math.isfinite(tgt) or tgt < -70:
        print("  audio stream is SILENT (no signal) — nothing to analyse or normalise")
        print("     this is normal for a text-on-screen edit exported with a silent track")
        return
    print(f"  loudness {ln['input_i']} LUFS   true peak {ln['input_tp']} dBFS   LRA {ln['input_lra']}")
    if tgt < -17:
        print(f"     -> quiet; normalising to -14 would add {-14 - tgt:.1f} LU")
    clip = re.search(r"histogram_0db: (\d+)",
                     sh(["ffmpeg", "-hide_banner", "-i", str(v), "-vn",
                         "-af", "volumedetect", "-f", "null", "/dev/null"]).stderr)
    print(f"  samples at 0dBFS: {clip.group(1) if clip else 0}")

    lo, mid, hi = band(v, "lowpass=f=80"), band(v, "highpass=f=150,lowpass=f=6000"), band(v, "highpass=f=8000")
    if lo is not None and mid is not None:
        gap = mid - lo
        verdict = "healthy" if gap > 12 else ("some rumble" if gap > 6 else "HEAVY rumble/wind")
        print(f"  sub-80Hz {lo:.1f} dB vs voice {mid:.1f} dB  -> {gap:.1f} dB gap ({verdict})")
    if hi is not None:
        print(f"  >8kHz {hi:.1f} dB" + ("  (dull mic; a presence lift helps)" if hi < -40 else ""))

    ps = pauses(v)
    if ps:
        longest = max(b - a2 for a2, b in ps)
        total = sum(b - a2 for a2, b in ps)
        lead = next((b - a2 for a2, b in ps if a2 <= 0.05), 0.0)
        print(f"  {len(ps)} pauses >0.30s   total {total:.1f}s ({100*total/i['dur']:.0f}%)   longest {longest:.2f}s")
        if lead:
            print(f"  dead air before first word: {lead:.2f}s  <- usually worth trimming")
        if longest < 0.9:
            print("     -> no genuinely long pauses; do NOT cut mid-sentence")
        for a2, b in ps:
            if b - a2 > 0.9:
                print(f"     long pause {b-a2:.2f}s at {a2:.1f}s")
    else:
        print("  no pauses detected")


def cmd_grid(a):
    v = Path(a.video).expanduser().resolve()
    i = info(v)
    out = a.output or "grid.png"
    t = a.time if a.time is not None else i["dur"] * 0.4
    tmp = "/tmp/_gridsrc.png"
    sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(v),
        "-frames:v", "1", "-vf", f"scale={a.width}:-2", tmp])
    from PIL import Image, ImageDraw
    im = Image.open(tmp).convert("RGB")
    d = ImageDraw.Draw(im)
    w, h = im.size
    for k in range(21):
        f = k / 20
        y = int(h * f)
        col = (255, 60, 60) if abs(f - 0.5) < 1e-6 else (0, 255, 255)
        d.line([(0, y), (w, y)], fill=col, width=2)
        d.text((5, y + 3), f"{f:.2f}  y={int(i['h']*f)}", fill=col)
    for k in range(11):
        f = k / 10
        x = int(w * f)
        d.line([(x, 0), (x, h)], fill=(255, 200, 0), width=1)
        d.text((x + 3, 4), f"x={int(i['w']*f)}", fill=(255, 200, 0))
    im.save(out)
    print(f"{out}  (source {i['w']}x{i['h']}; labels are source pixels)")


def cmd_contact(a):
    v = Path(a.video).expanduser().resolve()
    i = info(v)
    n = a.count
    tiles = []
    for k in range(n):
        t = i["dur"] * (k + 0.5) / n
        p = f"/tmp/_ct{k}.png"
        sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(v),
            "-frames:v", "1", "-vf", f"scale={a.tile}:-2", p])
        tiles.append(p)
    args = []
    for p in tiles:
        args += ["-i", p]
    lbl = "".join(f"[{k}]" for k in range(n))
    sh(["ffmpeg", "-y", "-v", "error"] + args +
       ["-filter_complex", f"{lbl}hstack=inputs={n}", "-frames:v", "1", a.output])
    print(a.output)


# ── render ─────────────────────────────────────────────────

PAUSE_PRESETS = {           # (long-pause threshold, how much to leave)
    "off":    (None, None),
    "gentle": (1.20, 0.45),
    "tight":  (0.50, 0.32),
}


def keep_ranges(v, dur, preset, lead_keep, tail_keep):
    thresh, keep = PAUSE_PRESETS[preset]
    cuts, notes = [], []
    for s, e in pauses(v):
        d = e - s
        if s <= 0.05:
            if lead_keep is not None and d > lead_keep:
                cuts.append((0.0, e - lead_keep)); notes.append(f"lead {d:.2f}s")
        elif e >= dur - 0.05:
            if tail_keep is not None and d > tail_keep:
                cuts.append((s + tail_keep, dur)); notes.append(f"tail {d:.2f}s")
        elif thresh is not None and d > thresh:
            cuts.append((s + keep / 2, e - keep / 2)); notes.append(f"{d:.2f}s@{s:.0f}s")
    ks, pos = [], 0.0
    for x, y in sorted(cuts):
        if x > pos:
            ks.append((pos, x))
        pos = max(pos, y)
    if pos < dur:
        ks.append((pos, dur))
    ks = [(x, y) for x, y in ks if y - x > 0.04]
    return ks, sum(y - x for x, y in cuts), notes


def aspect_filter(i, aspect, fit, crop_y, scale_w):
    """Return (filter_string, out_w, out_h)."""
    if aspect == "keep":
        ow = scale_w
        oh = int(round(scale_w * i["h"] / i["w"] / 2) * 2)
        return f"scale={ow}:{oh}:flags=lanczos", ow, oh
    aw, ah = (int(x) for x in aspect.split(":"))
    ow = scale_w
    oh = int(round(scale_w * ah / aw / 2) * 2)
    if fit == "pad":
        # blurred fill behind a fully-visible frame — loses nothing
        return (f"scale={ow}:{oh}:force_original_aspect_ratio=increase,"
                f"crop={ow}:{oh},gblur=sigma=28,eq=brightness=-0.06[bgp];"
                f"[0:v]scale={ow}:{oh}:force_original_aspect_ratio=decrease[fgp];"
                f"[bgp][fgp]overlay=(W-w)/2:(H-h)/2"), ow, oh
    # crop: scale so the short side fills, then take a window
    src_ar, dst_ar = i["w"] / i["h"], ow / oh
    if src_ar > dst_ar:                       # too wide -> crop sides
        sh_ = oh
        sw = int(round(i["w"] * oh / i["h"] / 2) * 2)
        x = int((sw - ow) * crop_y)
        return f"scale={sw}:{sh_}:flags=lanczos,crop={ow}:{oh}:{max(0,x)}:0", ow, oh
    sw = ow                                    # too tall -> crop top/bottom
    sh_ = int(round(i["h"] * ow / i["w"] / 2) * 2)
    y = int((sh_ - oh) * crop_y)
    return f"scale={sw}:{sh_}:flags=lanczos,crop={ow}:{oh}:0:{max(0,y)}", ow, oh


def cmd_render(a):
    v = Path(a.video).expanduser().resolve()
    if not v.is_file():
        die(f"no such file: {v}")
    i = info(v)
    print(f"→ {v.name}  {i['w']}x{i['h']}  {i['dur']:.2f}s")

    # ---- cuts
    silent = i["audio"] and not math.isfinite(float(loudness(v)["input_i"]))
    if i["audio"] and a.pauses != "off" and not silent:
        ks, removed, notes = keep_ranges(v, i["dur"], a.pauses,
                                         None if a.no_lead_trim else a.lead_keep,
                                         None if a.no_tail_trim else a.tail_keep)
        print(f"  cuts: {removed:.2f}s removed ({', '.join(notes) if notes else 'nothing'})")
    else:
        ks, removed = [(0.0, i["dur"])], 0.0
        print("  cuts: none")

    # ---- audio chain
    achain = ""
    if i["audio"] and a.audio != "none":
        base = AUDIO_REPAIR if a.audio == "repair" else ""
        ln = loudness(v, base)
        if not math.isfinite(float(ln["input_i"])) or float(ln["input_i"]) < -70:
            print("  audio: silent track — leaving it alone")
            ln = None
        else:
            print(f"  audio: {a.audio}; {ln['input_i']} LUFS -> {a.lufs}")
        if ln:
            norm = (f"loudnorm=I={a.lufs}:TP=-1.5:LRA=11:measured_I={ln['input_i']}:"
                    f"measured_TP={ln['input_tp']}:measured_LRA={ln['input_lra']}:"
                    f"measured_thresh={ln['input_thresh']}:offset={ln['target_offset']}:linear=true")
            achain = (base + "," if base else "") + norm
    elif i["audio"]:
        print("  audio: untouched")

    vf, ow, oh = aspect_filter(i, a.aspect, a.fit, a.crop_y, a.scale)
    grade = GRADE_LIGHT if a.grade == "light" else ""
    print(f"  output {ow}x{oh}  fit={a.fit if a.aspect!='keep' else '-'}  grade={a.grade}")

    # ---- build graph
    parts, n = [], len(ks)
    for k, (s, e) in enumerate(ks):
        parts.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{k}];")
        if i["audio"]:
            parts.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{k}];")
    if i["audio"]:
        parts.append("".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac];")
    else:
        parts.append("".join(f"[v{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=0[vc];")

    tail = f",{grade}" if grade else ""
    if a.fit == "pad" and a.aspect != "keep":
        # aspect_filter returned a two-stream graph; it consumes [0:v] itself
        parts.append(f"[vc]split=2[vc1][vc2];[vc1]{vf.replace('[0:v]','[vc2]')}"
                     f"{tail},setsar=1,fps={a.fps}[vout];")
    else:
        parts.append(f"[vc]{vf}{tail},setsar=1,fps={a.fps}[vout];")
    if i["audio"]:
        parts.append(f"[ac]{achain}[aout]" if achain else "[ac]anull[aout]")
    else:
        parts.append("anullsrc=channel_layout=stereo:sample_rate=48000[aout]")

    graph = "".join(parts).rstrip(";")
    cmd = ["ffmpeg", "-y", "-v", "error", "-stats", "-i", str(v)]
    if not i["audio"]:
        cmd += ["-f", "lavfi", "-t", f"{i['dur']:.3f}",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        graph = graph.replace("anullsrc=channel_layout=stereo:sample_rate=48000[aout]", "[1:a]anull[aout]")
    cmd += ["-filter_complex", graph, "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-crf", str(a.crf), "-preset", a.preset,
            "-pix_fmt", "yuv420p", "-maxrate", a.maxrate, "-bufsize", a.bufsize,
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"] + COMPAT + [a.output]
    if subprocess.run(cmd).returncode != 0:
        die("render failed")
    sz = Path(a.output).stat().st_size / 1e6
    print(f"✓ {a.output}  ({sz:.1f} MB)")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("probe"); q.add_argument("video"); q.set_defaults(fn=cmd_probe)

    g = sub.add_parser("grid"); g.add_argument("video")
    g.add_argument("-o", "--output"); g.add_argument("-t", "--time", type=float)
    g.add_argument("--width", type=int, default=520); g.set_defaults(fn=cmd_grid)

    c = sub.add_parser("contact"); c.add_argument("video")
    c.add_argument("-o", "--output", default="contact.png")
    c.add_argument("-n", "--count", type=int, default=6)
    c.add_argument("--tile", type=int, default=300); c.set_defaults(fn=cmd_contact)

    r = sub.add_parser("render"); r.add_argument("video")
    r.add_argument("-o", "--output", required=True)
    r.add_argument("--aspect", default="keep", help="keep | 9:16 | 1:1 | 16:9 | 4:5")
    r.add_argument("--fit", default="crop", choices=["crop", "pad"])
    r.add_argument("--crop-y", type=float, default=0.5,
                   help="0..1 window position when cropping (0=top). Measure with `grid` first.")
    r.add_argument("--scale", type=int, default=1080, help="output width")
    r.add_argument("--pauses", default="gentle", choices=list(PAUSE_PRESETS))
    r.add_argument("--lead-keep", type=float, default=0.10)
    r.add_argument("--tail-keep", type=float, default=0.30)
    r.add_argument("--no-lead-trim", action="store_true")
    r.add_argument("--no-tail-trim", action="store_true")
    r.add_argument("--audio", default="level", choices=["none", "level", "repair"])
    r.add_argument("--lufs", default="-14")
    r.add_argument("--grade", default="none", choices=["none", "light"])
    r.add_argument("--fps", type=int, default=30)
    r.add_argument("--crf", type=int, default=20)
    r.add_argument("--preset", default="medium")
    r.add_argument("--maxrate", default="10M"); r.add_argument("--bufsize", default="20M")
    r.set_defaults(fn=cmd_render)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
