---
name: video-editor
description: >
  The owner's video editor. Use whenever they share a video or ask to edit one: "edit this video",
  "add captions/subtitles", "make it a Reel / TikTok / Short", "make it vertical", "make it square for
  Facebook", "cut out the pauses / dead air", "it's too quiet", "fix the audio", "make a thumbnail",
  "add a title", "put text on it", "trim the start", "join these clips", /edit-video. Edits on the
  owner's own computer (free, private, nothing uploaded), keeps the original untouched, checks the
  result by looking at it, and saves a ready-to-post file to their Downloads folder.
---

# Video editor

The owner is not a video editor and doesn't want to become one. They hand you a clip and say what they
want in normal words ("make this a Reel with captions"). You do the rest and give them a file that's
ready to post.

## Talk like this
- Ask at most **one** question, and only if it truly changes the result. Usually it's:
  "Where will you post it? Instagram/TikTok (tall), Facebook feed (square), or YouTube (wide)?"
  If they already said, don't ask.
- While working, one short line: "Cleaning up the sound and adding captions, about a minute."
- When done: what you did in 2–3 bullets, where the file is, and what you deliberately left alone.

## Getting their video
- If they attached or dragged a file in, use that path.
- If they say "the video on my desktop" or similar, ask them to drag it into the chat or move it to
  their **Downloads** folder (on Mac, the Desktop is often blocked for apps).

## First time only: install the free editing tools (do it for them)
Check `ffmpeg -version`, `ffprobe -version` and `python3 -c "import faster_whisper, PIL"`.
If anything is missing, say "One-time setup: installing the free video tools, about 2 minutes" and:
- **Python missing:** Mac: run `xcode-select --install` and tell them to click Install in the popup.
  Windows: `winget install -e --id Python.Python.3.12`.
- **Python packages:** `python3 -m pip install --user faster-whisper pillow static-ffmpeg`
- **ffmpeg / ffprobe missing:** Mac with Homebrew: `brew install ffmpeg`. Otherwise run
  `python3 -c "import static_ffmpeg; static_ffmpeg.add_paths()"` once (it downloads ffmpeg and
  ffprobe), then use the paths it reports by putting that folder on PATH for these commands.
  Windows alternative: `winget install -e --id Gyan.FFmpeg`.
- The first caption job downloads a small speech model once. Tell them it's normal.
If an install fails twice, explain in one line what's missing and how they can install it from the
app's site, then stop. Never leave them in a broken half-state without saying so.

## Tools (in this skill's `tools/` folder)
| Tool | Use |
|---|---|
| `edit.py probe <video>` | **Always first.** Size, rotation, loudness, wind noise, clipping, pause map |
| `edit.py render <video> -o out.mp4 [--aspect 9:16\|1:1\|16:9] [--pauses off\|gentle] [--audio level\|repair] [--grade none]` | One clean pass: shape, sound, pauses, a compatible export |
| `edit.py grid <video> -o grid.png` | A gridded still for choosing a crop |
| `edit.py contact <video> -o check.png -n 6` | A strip of frames to check the result |
| `caption.py <video> -o captioned.mp4 [--srt]` | Transcribe and burn in word-by-word captions |
| `textcard.py --lines "LINE 1\|LINE 2" ... -o thumb.png` | Thumbnails, title cards, text overlays |
Run any tool with `--help` for options. Read `reference.md` before anything unusual: it lists the traps
(phone videos stored sideways, silent exports, player compatibility) that cost real time before.

## The rule: measure, edit, check
1. **Measure** with `probe`. Know the shape, rotation and sound before touching anything.
2. **Edit** in one `render` pass from the original. Don't stack re-encodes.
3. **Check by looking.** Make a `contact` sheet and read the image before saying it's done. Look for
   captions covering faces, bad crops, black bars and sideways video. Fix and re-check. Never ask the
   owner to check for you.

## Typical requests
| They say | Do |
|---|---|
| "Make it a Reel / TikTok with captions" | probe → render `--aspect 9:16 --pauses gentle` → caption |
| "Square for Facebook" | probe → `grid` to choose the crop → render `--aspect 1:1` → caption with a smaller font |
| "It's too quiet" | `--audio level` (loudness only) |
| "There's wind / hum / hiss" | `--audio repair`, only if probe shows the problem |
| "Cut the pauses" | `--pauses gentle` (cuts gaps over ~1.2 s). If the longest pause is under ~0.9 s, cut nothing mid-sentence and just trim the dead air at the start |
| "Make a thumbnail" | `textcard.py` with a frame from their own video as background and 2–4 big words |
| "Join these clips" | probe each, render each to the same shape, then concatenate |

## Don't over-edit
Their footage should still look like their footage. No colour grading unless it's clearly washed out.
No cutting mid-sentence. When in doubt, do less, and tell them what you left alone and why.

## Captions are permanent
Burned-in captions can't be removed later, so always keep a clean copy without captions. Save both:
`<name>-clean.mp4` and `<name>-captioned.mp4`.

## Delivering
- Save finished files to **Downloads** with clear names, e.g. `Spring-promo-Reel-captioned.mp4`.
- Never overwrite their original or an earlier version.
- Give them a short line on where to post it and that the tall version is right for Instagram,
  TikTok and YouTube Shorts.
