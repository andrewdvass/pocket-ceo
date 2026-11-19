"""Subscription check. The owner's purchase email is saved once (license activate); the plugin asks the
licence server at most once a day and keeps working offline for 7 days after the last good check.
Never blocks the owner from their own files: an inactive subscription only switches off the assistant."""
import datetime, getpass, hashlib, json, platform, urllib.request
from pathlib import Path
from . import data_dir

CONF = Path(__file__).resolve().parent.parent.parent / "license.json"
OFFLINE_GRACE_DAYS = 7


def conf():
    try:
        return json.loads(CONF.read_text())
    except (OSError, ValueError):
        return {"endpoint": None}


def _file():
    return data_dir() / ".license.json"


def _device():
    return hashlib.sha256(("%s|%s" % (platform.node(), getpass.getuser())).encode()).hexdigest()[:16]


def _save(d):
    _file().parent.mkdir(parents=True, exist_ok=True)
    _file().write_text(json.dumps(d, indent=1))


def _ask(endpoint, email, github=None, timeout=6):
    body = json.dumps({"email": email, "device": _device(), **({"github": github} if github else {})}).encode()
    req = urllib.request.Request(endpoint.rstrip("/") + "/check", data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def activate(email, github=None):
    c = conf()
    if not c.get("endpoint"):
        return {"active": True, "status": "checks_off"}
    r = _ask(c["endpoint"], email, github)
    _save({"email": email, "status": r.get("status"), "active": bool(r.get("active")),
           "last_ok": datetime.date.today().isoformat() if r.get("active") else None, "checked": datetime.date.today().isoformat()})
    return r


def status(today=None):
    today = today or datetime.date.today()
    c = conf()
    if not c.get("endpoint"):
        return {"active": True, "status": "checks_off"}
    try:
        d = json.loads(_file().read_text())
    except (OSError, ValueError):
        return {"active": False, "status": "not_activated", "buy_url": c.get("buy_url")}
    if d.get("checked") != today.isoformat():
        try:
            r = _ask(c["endpoint"], d["email"])
            d.update(status=r.get("status"), active=bool(r.get("active")), checked=today.isoformat())
            if d["active"]:
                d["last_ok"] = today.isoformat()
            _save(d)
        except Exception:
            last = d.get("last_ok")
            if last and (today - datetime.date.fromisoformat(last)).days <= OFFLINE_GRACE_DAYS:
                return {"active": True, "status": "offline_grace", "email": d.get("email")}
            return {"active": False, "status": "offline_too_long", "email": d.get("email")}
    return {"active": bool(d.get("active")), "status": d.get("status"), "email": d.get("email"), "buy_url": c.get("buy_url")}
