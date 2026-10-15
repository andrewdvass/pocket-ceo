# Reference — traps, recipes, and why

Everything here cost real rework at least once. Read before improvising.

## Traps

### A silent export needs a silent audio TRACK, not `-an`
Exporting with `-an` produces a file with **no audio stream at all**. It is
technically valid, decodes clean, passes every probe — and QuickTime, Photos,
CapCut and the Instagram/TikTok uploaders will refuse it or fail to play it.
This wasted a whole debugging round.

Always mux a silent track instead:
```
-f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 -shortest
```
`edit.py render` does this automatically for silent sources.

### Phone video is stored landscape with a rotation flag
A 4K vertical iPhone clip probes as `3840x2160` with `rotation=-90`. ffmpeg
applies rotation on decode, so filters and libass see `2160x3840`, but naive
`ffprobe stream=width,height` reports the coded size. Sizing captions off the
coded dimensions renders them for the wrong aspect ratio entirely.

`edit.py info()` and `caption.py probe()` both swap w/h when rotation is ±90.

### B-frames produce negative start DTS
Legal, but some macOS players and uploaders reject it. Ship with `-bf 0` so
DTS == PTS. Full profile below.

### Burned captions are permanent
See SKILL.md. Keep the pre-caption master.

### `subtitles=` vs `ass=`
Use `ass=` for a styled `.ass` — it honours the file's own styles. `subtitles=`
re-applies defaults. libass scales `PlayResX/Y` to the output frame, so an
`.ass` authored at 2160x3840 burns correctly onto 1080x1920 **as long as the
aspect matches**. It does not letterbox; mismatched aspect distorts the text.

### drawtext can't find fonts by name
This ffmpeg build has fontconfig enabled but its compiled-in config path does
not exist. Without `FONTCONFIG_FILE` set, `font='Helvetica'` silently fails.
The `~/.local/bin/ffmpeg` wrapper exports it already — but if you shell out to
the raw binary, set it yourself. Prefer `fontfile=` or PIL overlays.

### Crossfading two captioned clips mushes the text
With `xfade`, both text blocks dissolve through each other and neither is
readable. Stagger them: fade each text block **out before** its transition
starts and the next **in after** it finishes. Overlay text as a separate timed
stream, not burned into the slide.

```
[4:v]format=rgba,fade=t=in:st=0.15:d=0.25:alpha=1,
                 fade=t=out:st=2.70:d=0.20:alpha=1[t1];
[p0][t1]overlay=0:0:eof_action=repeat,format=yuv420p[v1];
[v1][v2]xfade=transition=fade:duration=0.35:offset=3.05[x1]
```
`xfade` offset = cumulative length so far minus the transition duration.

### zsh, not bash
- Unquoted `$var` is **not** word-split. `ffmpeg $args` passes one argument.
  Use `${=args}` or an array.
- `$O1[x1]` is parsed as an array subscript. Write `${O1}[x1]`.
- `s=900:200` is invalid for lavfi `color`; it is `s=900x200`.
- `-frames:v 1` is an **output** option — it must follow all `-i` inputs.

### volumedetect / silencedetect parsing
`silence_duration` is not field 5. Parse with
`grep -oE "silence_duration: [0-9.]+"`. A fully silent track reports the entire
file as one pause and `-inf` LUFS — guard for it.

## Encode profile

Maximum compatibility, used by `edit.py render`:
```
-c:v libx264 -profile:v main -level 4.0 -crf 20 -preset medium
-bf 0 -g 60 -keyint_min 30 -pix_fmt yuv420p -maxrate 10M -bufsize 20M
-color_primaries bt709 -color_trc bt709 -colorspace bt709
-c:a aac -b:a 192k -ar 48000 -ac 2
-video_track_timescale 30000 -avoid_negative_ts make_zero
-movflags +faststart -map_metadata -1
```
CRF 20–21 at 1080p lands ~45–55 MB per minute. CRF 17–18 roughly doubles that;
only worth it for an intermediate you will encode again.

Check faststart: `moov` must appear before `mdat`.

## Aspect ratio

Downscaling 4K → 1080p is itself a sharpening operation; the result looks
crisper than native 1080p. Prefer working from the original.

- **crop** — keeps the subject large, discards frame. Right for talking heads,
  especially vertical → square where the top is usually empty ceiling.
  Measure with `edit.py grid` and pass `--crop-y`; never guess.
- **pad** — blurred fill behind the whole frame. Loses nothing, shrinks the
  subject. Right when the subject is off-centre or motion would break a crop.

Landscape → 9:16 discards ~65% of the width. If the subject isn't centred, pad.

## Audio

Measure bands before reaching for filters:
- sub-80 Hz **15–25 dB** below the voice band = healthy, high-pass not needed.
- Under ~5 dB = heavy wind/rumble. A 2-pole high-pass (12 dB/oct) is not enough;
  chain two for 24 dB/oct. One pass at 12 dB/oct moved the ratio only 2.9 dB;
  doubling the slope got 5.2 dB.
- Quiet above 8 kHz = dull mic; a +2.5 dB shelf around 3 kHz adds intelligibility.

Targets: **−14 LUFS**, true peak −1.5 dBFS. Phone footage commonly arrives at
−22 to −25 LUFS, which plays noticeably quiet.

Loudnorm is two-pass: measure, then pass `measured_*` back with `linear=true`.
Measuring on the uncut source is fine — loudnorm gates silence, so trimming
pauses barely moves integrated loudness.

Denoise lightly. Car and room tone have a constant floor; pushing `afftdn` hard
puts an audible warble on speech.

## Whisper

`faster-whisper`, `small` model, ~2–3× realtime on this Mac, cached in
`~/.cache/huggingface`. `medium` for messy audio. Word timestamps drive the
highlight; Whisper splits hyphenated words ("follow" + "-up") so tokens are
rejoined by punctuation rules in `caption.py`.

## Environment

- **No Homebrew.** `ffmpeg`/`ffprobe` 7.1 are wrappers in `~/.local/bin` over a
  pip-bundled static build and Remotion's binary. Never suggest `brew install`.
- `~/Desktop` is unreadable (macOS TCC). `~/Downloads` is fine.
- Fonts: Arial Black, Impact, Helvetica at `/System/Library/Fonts/Supplemental/`.
