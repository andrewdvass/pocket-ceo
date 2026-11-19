"""Spots what the owner keeps coming back to, so Pocket CEO can offer to build a skill for it.

Every daily log (memory/log/YYYY-MM-DD.md) ends each conversation section with a line like
`Topics: pricing, hiring, google-ads`. This counts topics over a window and returns the ones that
recur often enough to deserve their own skill and don't have one yet. Built skills live in
~/.claude/skills/pceo-<topic>/ (personal skills Claude loads in every session); declined ones are
remembered in memory/patterns.md so the same offer isn't made twice.
"""
import datetime, re
from pathlib import Path
from . import data_dir

BUILT_IN = {"tax", "taxes", "accounting", "gst", "hst", "receipts", "cash", "cashflow", "cash-flow", "invoices",
            "collections", "contracts", "legal", "email", "inbox", "growth", "marketing-plan", "hiring", "video",
            "brief", "memory", "ai", "google-ads", "ppc", "meetings", "meeting-prep", "debrief", "decisions"}


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def skills_dir():
    return Path.home() / ".claude" / "skills"


def existing_skills():
    d = skills_dir()
    return {p.name[5:] for p in d.glob("pceo-*") if p.is_dir()} if d.exists() else set()


def declined():
    p = data_dir() / "memory" / "patterns.md"
    if not p.exists():
        return set()
    return {slug(m.group(1)) for m in re.finditer(r"declined:\s*([^\n|]+)", p.read_text(encoding="utf-8"), re.I)}


def topic_counts(days=45, today=None):
    today = today or datetime.date.today()
    logs = data_dir() / "memory" / "log"
    counts, seen_days, examples = {}, {}, {}
    for f in sorted(logs.glob("20??-??-??.md")) if logs.exists() else []:
        try:
            d = datetime.date.fromisoformat(f.stem)
        except ValueError:
            continue
        if (today - d).days > days:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"^\s*[-*]?\s*Topics?:\s*(.+)$", text, re.M | re.I):
            for t in re.split(r"[,;]", m.group(1)):
                s = slug(t)
                if not s:
                    continue
                counts[s] = counts.get(s, 0) + 1
                seen_days.setdefault(s, set()).add(d)
                examples.setdefault(s, f.stem)
    return counts, seen_days, examples


def suggestions(days=45, min_times=3, min_days=3, today=None):
    """Topics raised at least `min_times` times on at least `min_days` different days."""
    counts, seen, ex = topic_counts(days, today)
    have, no = existing_skills(), declined()
    out = []
    for t, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if n >= min_times and len(seen[t]) >= min_days and t not in BUILT_IN and t not in have and t not in no:
            out.append({"topic": t, "times": n, "days": len(seen[t]), "first_seen": min(seen[t]).isoformat(),
                        "last_seen": max(seen[t]).isoformat()})
    return {"window_days": days, "suggest": out, "already_built": sorted(have), "declined": sorted(no),
            "top_topics": sorted(counts.items(), key=lambda kv: -kv[1])[:12]}


def create_skill(topic, description, body, knowledge=None):
    """Write ~/.claude/skills/pceo-<topic>/SKILL.md (+ knowledge/*.md). Refuses to overwrite."""
    s = slug(topic)
    d = skills_dir() / ("pceo-" + s)
    if d.exists():
        raise SystemExit("A skill for %s already exists at %s. Edit it instead of replacing it." % (topic, d))
    (d / "knowledge").mkdir(parents=True)
    desc = " ".join(description.split())
    (d / "SKILL.md").write_text("---\nname: pceo-%s\ndescription: >\n  %s\n---\n\n%s\n" % (s, desc, body.strip()), encoding="utf-8")
    for name, text in (knowledge or {}).items():
        (d / "knowledge" / (slug(Path(name).stem) + ".md")).write_text(text.strip() + "\n", encoding="utf-8")
    log = data_dir() / "memory" / "patterns.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write("- %s | built: %s | %s\n" % (datetime.date.today().isoformat(), s, d))
    return str(d)


def decline(topic):
    log = data_dir() / "memory" / "patterns.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write("- %s | declined: %s\n" % (datetime.date.today().isoformat(), slug(topic)))
