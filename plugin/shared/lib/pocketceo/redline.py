"""Make a Word document with real tracked changes (and a margin comment explaining each one).

Input: the contract as .docx (formatting of untouched paragraphs is kept exactly) or plain text, and a
list of changes: [{"find": "exact text from the contract", "replace": "new text" (or "" to delete),
"comment": "why, in plain words"}]. A change whose `find` text is not in the document is reported, never
guessed. Standard library only. Opens in Word, Pages and Google Docs, which show the changes as
suggestions the other side can accept or reject.
"""
import datetime, html, re, zipfile
from pathlib import Path
from xml.sax.saxutils import escape

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
AUTHOR = "Pocket CEO (for review)"


def _norm(s):
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("“", '"').replace("”", '"')).strip()


def _t(text, tag="w:t"):
    return '<%s xml:space="preserve">%s</%s>' % (tag, escape(text), tag)


def _paragraph_text(p_xml):
    parts = re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>|<w:tab/>", p_xml, re.S)
    return html.unescape("".join(x if x else "" for x in parts))


def _first_rpr(p_xml):
    m = re.search(r"<w:r(?:\s[^>]*)?>\s*(<w:rPr>.*?</w:rPr>)", p_xml, re.S)
    return m.group(1) if m else ""


def _ppr(p_xml):
    m = re.search(r"<w:pPr>.*?</w:pPr>", p_xml, re.S)
    return m.group(0) if m else ""


class _Ids:
    def __init__(self):
        self.rev = 100
        self.comment = 0
        self.comments = []
        self.date = datetime.datetime.now().replace(microsecond=0).isoformat() + "Z"

    def next_rev(self):
        self.rev += 1
        return self.rev


def _rebuild(p_xml, text, hits, ids):
    """Rebuild one paragraph: plain runs around tracked deletions/insertions, with comment ranges."""
    rpr = _first_rpr(p_xml)
    out, pos = [], 0
    run = lambda s: '<w:r>%s%s</w:r>' % (rpr, _t(s)) if s else ""
    for start, end, ch in sorted(hits, key=lambda h: h[0]):
        out.append(run(text[pos:start]))
        cid = None
        if ch.get("comment"):
            cid = ids.comment
            ids.comment += 1
            ids.comments.append((cid, ch["comment"]))
            out.append('<w:commentRangeStart w:id="%d"/>' % cid)
        a = 'w:author="%s" w:date="%s"' % (escape(AUTHOR), ids.date)
        if text[start:end]:
            out.append('<w:del w:id="%d" %s><w:r>%s%s</w:r></w:del>' % (ids.next_rev(), a, rpr, _t(text[start:end], "w:delText")))
        if ch.get("replace"):
            out.append('<w:ins w:id="%d" %s><w:r>%s%s</w:r></w:ins>' % (ids.next_rev(), a, rpr, _t(ch["replace"])))
        if cid is not None:
            out.append('<w:commentRangeEnd w:id="%d"/><w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="%d"/></w:r>' % (cid, cid))
        pos = end
    out.append(run(text[pos:]))
    return "<w:p>%s%s</w:p>" % (_ppr(p_xml), "".join(out))


def _locate(text, find):
    """Exact match first, then a match that ignores spacing and curly quotes, mapped back to the original."""
    i = text.find(find)
    if i >= 0:
        return i, i + len(find)
    trans = {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " "}
    norm, where, space = [], [], True
    for k, c in enumerate(text):
        c = trans.get(c, c)
        if c.isspace():
            if not space:
                norm.append(" "); where.append(k)
            space = True
        else:
            norm.append(c); where.append(k); space = False
    nt, nf = "".join(norm), _norm(find)
    j = nt.find(nf) if nf else -1
    if j < 0:
        return None
    return where[j], where[j + len(nf) - 1] + 1


def _comments_xml(ids):
    items = "".join(
        '<w:comment w:id="%d" w:author="%s" w:date="%s" w:initials="PC"><w:p><w:r>%s</w:r></w:p></w:comment>'
        % (cid, escape(AUTHOR), ids.date, _t(text)) for cid, text in ids.comments)
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:comments xmlns:w="%s">%s</w:comments>' % (W, items)


def _minimal_docx(paragraphs):
    body = "".join("<w:p><w:r>%s</w:r></w:p>" % _t(p) for p in paragraphs)
    doc = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="%s"><w:body>%s<w:sectPr/></w:body></w:document>' % (W, body)
    return {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/_rels/document.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>',
        "word/document.xml": doc,
    }


def redline(src, changes, dest):
    src = Path(src)
    if src.suffix.lower() == ".docx":
        with zipfile.ZipFile(src) as z:
            parts = {n: z.read(n) for n in z.namelist()}
        parts = {k: (v.decode("utf-8") if k.endswith((".xml", ".rels")) else v) for k, v in parts.items()}
    else:
        text = src.read_text(encoding="utf-8", errors="replace")
        parts = _minimal_docx([l for l in text.splitlines()])
    doc = parts["word/document.xml"]
    ids = _Ids()
    done, missing = [], []
    pending = list(enumerate(changes))
    paras = list(re.finditer(r"<w:p(?:\s[^>]*)?>.*?</w:p>|<w:p(?:\s[^>]*)?/>", doc, re.S))
    new_doc, last = [], 0
    for m in paras:
        p_xml = m.group(0)
        if "<w:t" not in p_xml:
            continue
        text = _paragraph_text(p_xml)
        hits, taken = [], []
        for n, ch in list(pending):
            loc = _locate(text, ch["find"])
            if loc and not any(loc[0] < e and s < loc[1] for s, e in taken):
                hits.append((loc[0], loc[1], ch)); taken.append(loc); pending.remove((n, ch)); done.append(n)
        if hits:
            new_doc.append(doc[last:m.start()])
            new_doc.append(_rebuild(p_xml, text, hits, ids))
            last = m.end()
    new_doc.append(doc[last:])
    parts["word/document.xml"] = "".join(new_doc)
    missing = [ch["find"] for _, ch in pending]
    if ids.comments:
        parts["word/comments.xml"] = _comments_xml(ids)
        rels = parts["word/_rels/document.xml.rels"]
        if "comments.xml" not in rels:
            rels = rels.replace("</Relationships>", '<Relationship Id="rIdPceoComments" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/></Relationships>')
            parts["word/_rels/document.xml.rels"] = rels
        ct = parts["[Content_Types].xml"]
        if "/word/comments.xml" not in ct:
            parts["[Content_Types].xml"] = ct.replace("</Types>", '<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/></Types>')
    # turn on "track changes" so further edits by the other side are tracked too
    settings = parts.get("word/settings.xml")
    if settings and "<w:trackRevisions" not in settings:
        parts["word/settings.xml"] = re.sub(r"(<w:settings[^>]*>)", r"\1<w:trackRevisions/>", settings, count=1)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data.encode("utf-8") if isinstance(data, str) else data)
    return {"file": str(dest), "applied": len(done), "not_found": missing, "comments": len(ids.comments)}


def docx_text(path):
    """Plain text of a .docx, one paragraph per line (for reading a contract)."""
    with zipfile.ZipFile(path) as z:
        doc = z.read("word/document.xml").decode("utf-8")
    return "\n".join(_paragraph_text(m.group(0)) for m in re.finditer(r"<w:p(?:\s[^>]*)?>.*?</w:p>", doc, re.S))
