#!/usr/bin/env python3
"""
Burn social-style captions onto a video.

Transcribes the video's audio locally with faster-whisper (no API key, offline),
groups the words into short punchy chunks, and burns them in with ffmpeg/libass
in a TikTok / Reels / Shorts style — big bold text with the active word
highlighted as it is spoken.

    python3 caption.py clip.mp4
    python3 caption.py clip.mp4 --words 4 --model medium
    python3 caption.py clip.mp4 --highlight "#39FF14" --position 0.75
    python3 caption.py clip.mp4 --srt          # also write a sidecar .srt
    python3 caption.py clip.mp4 --ass-only     # build the .ass, skip the burn

First run downloads the Whisper model (~500MB for "small"); it is cached in
~/.cache/huggingface and reused after that.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MODELS = ["tiny", "base", "small", "medium", "large-v3"]

# Fonts verified present on this Mac. First one that exists wins.
FONT_STACK = ["Arial Black", "Impact", "Helvetica"]

# Fraction of the frame width captions may occupy. Social feeds crop and overlay
# UI near the edges, so leave a margin rather than running to the bezel.
SAFE_WIDTH = 0.88


# ─── helpers ────────────────────────────────────────────────

def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def need(binary):
    if not shutil.which(binary):
        die(f"{binary} not found on PATH")
    return binary


def rotation(video):
    """Display rotation in degrees, from side data or the legacy tag."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream_side_data=rotation",
         "-show_entries", "stream_tags=rotate",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
        capture_output=True, text=True,
    )
    for tok in out.stdout.split():
        try:
            return int(float(tok)) % 360
        except ValueError:
            continue
    return 0


def probe(video):
    """Return (width, height, duration) as *displayed*.

    Phone video is often stored landscape with a rotation flag; ffmpeg applies
    that on decode, so the frames the filters and libass see are swapped
    relative to the coded dimensions. Reading the coded size here would size
    and position every caption for the wrong aspect ratio.
    """
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        die(f"ffprobe failed on {video}:\n{out.stderr.strip()}")
    vals = [v for v in out.stdout.split() if v.strip()]
    if len(vals) < 3:
        die(f"could not read dimensions/duration from {video}")

    w, h, dur = int(vals[0]), int(vals[1]), float(vals[2])
    if rotation(video) in (90, 270):
        w, h = h, w
    return w, h, dur


def has_audio(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True,
    )
    return "audio" in out.stdout


def hex_to_ass(color):
    """#RRGGBB -> &HBBGGRR& (ASS is BGR, and drops the alpha byte here)."""
    c = color.lstrip("#").strip()
    if len(c) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", c):
        die(f"bad colour {color!r} — expected #RRGGBB")
    return f"&H00{c[4:6]}{c[2:4]}{c[0:2]}".upper() + "&"


def ass_time(t):
    """seconds -> H:MM:SS.cc"""
    t = max(0.0, float(t))
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def srt_time(t):
    t = max(0.0, float(t))
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    ms = int(round((s - int(s)) * 1000))
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"


def esc(text):
    """Make text safe to drop inside an ASS dialogue line."""
    return (text.replace("\\", "/")
                .replace("{", "(")
                .replace("}", ")")
                .replace("\n", " ")
                .strip())


# Whisper emits hyphenated and contracted words as separate tokens
# ("follow" + "-up"), so a plain " ".join gives "FOLLOW -UP".
NO_SPACE_BEFORE = ("-", "—", "'", "’", ",", ".", "!", "?", ":", ";", "%", ")", "]", "}")
NO_SPACE_AFTER = ("-", "—", "(", "[", "{", "’")


def join_tokens(pairs):
    """pairs: [(raw, rendered)] -> joined string with sane spacing."""
    out = ""
    for idx, (raw, rendered) in enumerate(pairs):
        if idx and not raw.startswith(NO_SPACE_BEFORE) and not pairs[idx - 1][0].endswith(NO_SPACE_AFTER):
            out += " "
        out += rendered
    return out


def pick_font(preferred=None):
    """Return (font_name, font_file_path_or_None)."""
    roots = [Path("/System/Library/Fonts/Supplemental"),
             Path("/System/Library/Fonts"),
             Path("/Library/Fonts"),
             Path.home() / "Library/Fonts",
             Path("C:/Windows/Fonts"),
             Path.home() / "AppData/Local/Microsoft/Windows/Fonts",
             Path("/usr/share/fonts/truetype/msttcorefonts")]
    win = {"Arial Black": "ariblk", "Impact": "impact", "Helvetica": "arial"}
    names = [preferred] if preferred else FONT_STACK
    for name in names:
        for r in roots:
            hits = sorted(r.glob(f"{name}.*")) or sorted(r.glob(f"{win.get(name, name)}.*"))
            if hits:
                return name, hits[0]
    return (preferred or "Helvetica"), None


def make_measurer(font_path, size):
    """Return fn(text)->pixel width, or None if it can't be measured."""
    if not font_path:
        return None
    try:
        from PIL import ImageFont
        f = ImageFont.truetype(str(font_path), size)
    except Exception:
        return None

    def width(text):
        try:
            b = f.getbbox(text)
            return b[2] - b[0]
        except Exception:
            return 0
    return width


# ─── transcription ──────────────────────────────────────────

def transcribe(video, model_size, language, workdir):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die("faster-whisper missing. Install with:\n"
            "  python3 -m pip install --user faster-whisper")

    wav = workdir / "audio.wav"
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(video),
         "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        die(f"could not extract audio:\n{r.stderr.strip()}")

    print(f"  transcribing with whisper '{model_size}' (first run downloads the model)…",
          flush=True)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(wav),
        language=language,
        word_timestamps=True,
        vad_filter=True,
        beam_size=5,
    )

    words = []
    for seg in segments:
        for w in (seg.words or []):
            txt = (w.word or "").strip()
            if not txt or w.start is None or w.end is None:
                continue
            words.append({"text": txt, "start": float(w.start), "end": float(w.end)})

    return words, info.language, getattr(info, "language_probability", None)


# ─── grouping ───────────────────────────────────────────────

def group_words(words, max_words, max_chars, pause, measure=None, max_px=None,
                uppercase=True):
    """Break the word stream into short caption chunks.

    When a measurer is supplied the line is capped by real rendered width, which
    is what actually matters — a character budget tuned for a 1080-wide video
    lets captions run past the edge of a 720-wide one.
    """
    def line_of(chunk, extra):
        toks = [x["text"] for x in chunk] + [extra["text"]]
        if uppercase:
            toks = [t.upper() for t in toks]
        return join_tokens([(t, t) for t in toks])

    groups, cur = [], []
    for w in words:
        if cur:
            gap = w["start"] - cur[-1]["end"]
            ends_sentence = re.search(r"[.!?…]$", cur[-1]["text"]) is not None
            candidate = line_of(cur, w)

            if measure and max_px:
                too_wide = measure(candidate) > max_px
            else:
                too_wide = len(candidate) > max_chars

            if len(cur) >= max_words or gap > pause or ends_sentence or too_wide:
                groups.append(cur)
                cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


# ─── ASS generation ─────────────────────────────────────────

def build_ass(groups, width, height, args, font):
    size = args.font_size
    outline = max(2, round(size * 0.09))
    shadow = max(0, round(size * 0.03))

    base = hex_to_ass(args.color)
    hot = hex_to_ass(args.highlight)
    edge = hex_to_ass(args.outline_color)

    cx, cy = width // 2, int(height * args.position)

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,{font},{size},{base},{base},{edge},&H64000000,-1,0,0,0,100,100,0,0,1,{outline},{shadow},5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # The active word is marked by colour only. Scaling individual words inline
    # would fight the line-level \t pop below (libass applies both to the whole
    # line), and it makes the text jitter as the highlight moves.
    def render(group, active):
        pairs = []
        for j, w in enumerate(group):
            t = esc(w["text"])
            if args.uppercase:
                t = t.upper()
            shown = f"{{\\c{hot}}}{t}{{\\c{base}}}" if j == active else t
            pairs.append((t, shown))
        return join_tokens(pairs)

    # scale up from 70% then settle — the classic caption "pop"
    POP = ("\\fscx70\\fscy70"
           "\\t(0,90,\\fscx108\\fscy108)"
           "\\t(90,170,\\fscx100\\fscy100)")

    lines = []
    for g in groups:
        g_start, g_end = g[0]["start"], g[-1]["end"]
        for i, w in enumerate(g):
            start = g_start if i == 0 else w["start"]
            end = g_end if i == len(g) - 1 else w["end"]
            if end <= start:
                end = start + 0.08

            tags = f"\\an5\\pos({cx},{cy})"
            if i == 0:
                tags += POP
            lines.append(
                f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Pop,,0,0,0,,"
                f"{{{tags}}}{render(g, i)}"
            )

    return head + "\n".join(lines) + "\n"


def build_srt(groups, uppercase):
    out = []
    for n, g in enumerate(groups, 1):
        toks = [w["text"].upper() if uppercase else w["text"] for w in g]
        text = join_tokens([(t, t) for t in toks]).strip()
        out.append(f"{n}\n{srt_time(g[0]['start'])} --> {srt_time(g[-1]['end'])}\n{text}\n")
    return "\n".join(out)


# ─── main ───────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="Burn social-style captions onto a video (local Whisper, no API key).")
    p.add_argument("video", help="input video file")
    p.add_argument("-o", "--output", help="output path (default: <name>-captioned.mp4)")
    p.add_argument("--model", default="small", choices=MODELS,
                   help="whisper model — bigger is more accurate but slower (default: small)")
    p.add_argument("--language", default=None,
                   help="force a language code e.g. 'en' (default: auto-detect)")
    p.add_argument("--words", type=int, default=3, dest="max_words",
                   help="max words shown at once (default: 3)")
    p.add_argument("--max-chars", type=int, default=22,
                   help="max characters shown at once (default: 22)")
    p.add_argument("--pause", type=float, default=0.55,
                   help="silence in seconds that forces a new caption (default: 0.55)")
    p.add_argument("--position", type=float, default=0.72,
                   help="vertical centre, 0=top 1=bottom (default: 0.72)")
    p.add_argument("--font-size", type=int, default=None,
                   help="override font size in px (default: ~5%% of video height)")
    p.add_argument("--font", default=None, help=f"font name (default: first of {FONT_STACK})")
    p.add_argument("--color", default="#FFFFFF", help="base text colour (default: #FFFFFF)")
    p.add_argument("--highlight", default="#FFE400",
                   help="active-word colour (default: #FFE400)")
    p.add_argument("--outline-color", default="#000000", help="outline colour (default: #000000)")
    p.add_argument("--no-uppercase", action="store_false", dest="uppercase",
                   help="keep original casing (default: UPPERCASE)")
    p.add_argument("--crf", type=int, default=18, help="x264 quality, lower=better (default: 18)")
    p.add_argument("--srt", action="store_true", help="also write a sidecar .srt")
    p.add_argument("--ass-only", action="store_true", help="write the .ass and stop (no burn)")
    args = p.parse_args()

    need("ffmpeg"); need("ffprobe")

    video = Path(args.video).expanduser().resolve()
    if not video.is_file():
        die(f"no such file: {video}")
    if not has_audio(video):
        die(f"{video.name} has no audio track — nothing to transcribe")

    width, height, duration = probe(video)
    font, font_path = pick_font(args.font)

    # settle the font size up front — both the grouping and the ASS need it
    if not args.font_size:
        args.font_size = max(18, round(height * 0.052))
    measure = make_measurer(font_path, args.font_size)
    max_px = width * SAFE_WIDTH

    out_path = Path(args.output).expanduser().resolve() if args.output \
        else video.with_name(f"{video.stem}-captioned.mp4")

    print(f"→ {video.name}  {width}x{height}  {duration:.1f}s")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        words, lang, prob = transcribe(video, args.model, args.language, tmp)
        if not words:
            die("no speech detected — is there actually talking in this video?")

        groups = group_words(words, args.max_words, args.max_chars, args.pause,
                             measure=measure, max_px=max_px,
                             uppercase=args.uppercase)
        conf = f" ({prob:.0%} confident)" if prob else ""
        fitted = "measured" if measure else f"{args.max_chars}-char"
        print(f"  {len(words)} words → {len(groups)} captions · language: {lang}{conf}")
        print(f"  {font} {args.font_size}px · {fitted} fit within {int(max_px)}px")

        ass_text = build_ass(groups, width, height, args, font)

        if args.srt:
            srt_path = out_path.with_suffix(".srt")
            srt_path.write_text(build_srt(groups, args.uppercase), encoding="utf-8")
            print(f"  wrote {srt_path}")

        if args.ass_only:
            ass_path = out_path.with_suffix(".ass")
            ass_path.write_text(ass_text, encoding="utf-8")
            print(f"  wrote {ass_path}")
            return

        # keep the .ass on a simple path — the ffmpeg filter syntax hates
        # colons, quotes and brackets in filenames
        ass_file = tmp / "captions.ass"
        ass_file.write_text(ass_text, encoding="utf-8")

        print(f"  burning in with {font}…", flush=True)
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-stats", "-i", str(video),
             "-vf", f"ass={ass_file.name}",
             "-c:v", "libx264", "-crf", str(args.crf), "-preset", "medium",
             "-pix_fmt", "yuv420p", "-c:a", "copy",
             str(out_path)],
            cwd=tmp, capture_output=True, text=True,
        )
        if r.returncode != 0:
            die(f"ffmpeg burn failed:\n{r.stderr.strip()}")

    mb = out_path.stat().st_size / 1e6
    print(f"✓ {out_path}  ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
