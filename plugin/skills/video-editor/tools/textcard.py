#!/usr/bin/env python3
"""
Text cards, overlays and thumbnails.

Transparent overlay to burn onto a clip:
  textcard.py --lines "POV: you said|you have a|marketing team" -o ov.png

Thumbnail over a blurred frame pulled from the video itself:
  textcard.py --lines "HE SPENT $1M|TESTING|FACEBOOK ADS" \
      --bg clip.mp4 --bg-time 40 --pill "DANIEL ILES" \
      --face clip.mp4 --face-box 328,120,360,360 -o thumb.png

Notes
  * font size auto-fits the longest line across ALL lines, so multi-card sets
    stay visually consistent — pass --font-size to pin it across separate runs
  * a blank line ("") inserts a paragraph gap
  * default look: Arial Black, uppercase, white with a heavy black
    outline, last line in yellow
"""
import argparse, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import os as _os

_CANDIDATES = {
    "black": ["/System/Library/Fonts/Supplemental/Arial Black.ttf", "C:/Windows/Fonts/ariblk.ttf"],
    "impact": ["/System/Library/Fonts/Supplemental/Impact.ttf", "C:/Windows/Fonts/impact.ttf"],
    "helvetica": ["/System/Library/Fonts/Helvetica.ttc", "C:/Windows/Fonts/arial.ttf"],
}
FONTS = {k: next((p for p in v if _os.path.exists(p)), v[0]) for k, v in _CANDIDATES.items()}


def hexc(c, a=255):
    c = c.lstrip("#")
    if len(c) != 6:
        sys.exit(f"bad colour {c!r}")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


def font(path, s):
    return ImageFont.truetype(path, s)


def grab(src, t, size):
    """Frame from a video, or an image file, resized to fill `size`."""
    p = Path(src).expanduser().resolve()
    if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        im = Image.open(p).convert("RGB")
    else:
        tmp = "/tmp/_tc_bg.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", str(p),
                        "-frames:v", "1", tmp], check=True)
        im = Image.open(tmp).convert("RGB")
    W, H = size
    sc = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
    return im.crop(((im.width - W) // 2, (im.height - H) // 2,
                    (im.width - W) // 2 + W, (im.height - H) // 2 + H))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lines", required=True, help='pipe-separated; "" makes a gap')
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--size", default="1080x1920")
    p.add_argument("--pos", type=float, default=0.70, help="vertical centre of the block, 0..1")
    p.add_argument("--font", default="black", choices=list(FONTS))
    p.add_argument("--font-size", type=int, default=None, help="pin size for consistency across cards")
    p.add_argument("--max-width", type=float, default=0.90)
    p.add_argument("--leading", type=float, default=0.42, help="x font size; raise it if text feels cramped")
    p.add_argument("--gap", type=float, default=0.55, help="paragraph gap, x font size")
    p.add_argument("--stroke", type=float, default=0.105)
    p.add_argument("--color", default="#FFFFFF")
    p.add_argument("--accent-color", default="#FFE400")
    p.add_argument("--accent", default="last", help="'last', 'none', or 0-based line indexes e.g. 0,2")
    p.add_argument("--no-uppercase", action="store_true")
    p.add_argument("--strike", type=int, default=None, help="strike through this line index")
    p.add_argument("--strike-color", default="#E83E3E")
    p.add_argument("--pill", default=None)
    p.add_argument("--pill-pos", type=float, default=0.205)
    p.add_argument("--pill-size", type=int, default=46)
    p.add_argument("--bg", default=None, help="video or image; omit for transparent")
    p.add_argument("--bg-time", type=float, default=1.0)
    p.add_argument("--blur", type=float, default=26)
    p.add_argument("--darken", type=float, default=0.52)
    p.add_argument("--face", default=None, help="video/image to take a circular inset from")
    p.add_argument("--face-time", type=float, default=None)
    p.add_argument("--face-box", default=None, help="x,y,w,h in SOURCE pixels (use edit.py grid)")
    p.add_argument("--face-pos", type=float, default=0.735)
    p.add_argument("--face-d", type=int, default=470)
    a = p.parse_args()

    W, H = (int(x) for x in a.size.lower().split("x"))
    fpath = FONTS[a.font]
    base, accent = hexc(a.color), hexc(a.accent_color)

    raw = a.lines.split("|")
    lines = [(t.strip() if a.no_uppercase else t.strip().upper()) for t in raw]

    if a.accent == "none":
        acc = set()
    elif a.accent == "last":
        acc = {max(i for i, t in enumerate(lines) if t)}
    else:
        acc = {int(x) for x in a.accent.split(",")}

    # ---- canvas
    if a.bg:
        img = grab(a.bg, a.bg_time, (W, H)).filter(ImageFilter.GaussianBlur(a.blur))
        img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), a.darken).convert("RGBA")
    else:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ---- size
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    if a.font_size:
        size = a.font_size
    else:
        longest = max((t for t in lines if t), key=len)
        size = 200
        while size > 14:
            b = probe.textbbox((0, 0), longest, font=font(fpath, size))
            if b[2] - b[0] <= W * a.max_width:
                break
            size -= 1
    f = font(fpath, size)
    stroke = max(4, round(size * a.stroke))
    lead, gap = round(size * a.leading), round(size * a.gap)

    # ---- pill
    if a.pill:
        pf = font(fpath, a.pill_size)
        pb = d.textbbox((0, 0), a.pill, font=pf)
        pw, ph = pb[2] - pb[0], pb[3] - pb[1]
        padx, pady = 34, 22
        x0 = (W - pw) / 2 - padx
        y0 = H * a.pill_pos - ph / 2 - pady
        d.rounded_rectangle([x0, y0, x0 + pw + padx * 2, y0 + ph + pady * 2],
                            radius=(ph + pady * 2) // 2, fill=accent)
        d.text(((W - pw) / 2 - pb[0], y0 + pady - pb[1]), a.pill, font=pf, fill=(0, 0, 0, 255))

    # ---- text block
    rows = []
    for t in lines:
        if not t:
            rows.append((None, 0, None))
        else:
            b = d.textbbox((0, 0), t, font=f)
            rows.append((t, b[3] - b[1], b))
    total = sum(h for _, h, _ in rows)
    for k in range(len(rows) - 1):
        total += gap if rows[k][0] is None or rows[k + 1][0] is None else lead

    y = H * a.pos - total / 2
    placed = []
    for k, (t, h, b) in enumerate(rows):
        if t:
            x = (W - (b[2] - b[0])) / 2 - b[0]
            col = accent if k in acc else base
            d.text((x + 4, y - b[1] + 6), t, font=f, fill=(0, 0, 0, 150),
                   stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
            d.text((x, y - b[1]), t, font=f, fill=col, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
            placed.append((k, x + b[0], y, h, b[2] - b[0]))
        if k < len(rows) - 1:
            y += h + (gap if t is None or rows[k + 1][0] is None else lead)

    if a.strike is not None:
        for k, x, yy, h, wdt in placed:
            if k == a.strike:
                th = max(6, round(size * 0.10))
                cy = yy + h / 2
                d.rectangle([x - 16, cy - th // 2, x + wdt + 16, cy + th // 2],
                            fill=hexc(a.strike_color))

    # ---- face inset
    if a.face:
        ft = a.face_time if a.face_time is not None else a.bg_time
        src = Path(a.face).expanduser().resolve()
        tmp = "/tmp/_tc_face.png"
        if src.suffix.lower() in (".png", ".jpg", ".jpeg"):
            fim = Image.open(src).convert("RGB")
        else:
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(ft), "-i", str(src),
                            "-frames:v", "1", tmp], check=True)
            fim = Image.open(tmp).convert("RGB")
        if a.face_box:
            x, yb, w, h = (int(v) for v in a.face_box.split(","))
            fim = fim.crop((x, yb, x + w, yb + h))
        side = min(fim.size)
        fim = fim.crop(((fim.width - side) // 2, (fim.height - side) // 2,
                        (fim.width - side) // 2 + side, (fim.height - side) // 2 + side))
        D = a.face_d
        fim = fim.resize((D, D), Image.LANCZOS)
        mask = Image.new("L", (D, D), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, D, D], fill=255)
        fx, fy = (W - D) // 2, int(H * a.face_pos - D / 2)
        ImageDraw.Draw(img).ellipse([fx - 12, fy - 12, fx + D + 12, fy + D + 12], fill=accent)
        img.paste(fim, (fx, fy), mask)

    out = Path(a.output).expanduser()
    if a.bg:
        img.convert("RGB").save(out)
    else:
        img.save(out)
    print(f"{out}  {W}x{H}  font {size}px  leading {lead}px")


if __name__ == "__main__":
    main()
