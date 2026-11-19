import json, re, tempfile, unittest, zipfile
from pathlib import Path
from xml.dom import minidom
from tests.helpers import ROOT  # noqa: F401  (sets the import path)
from pocketceo import redline

DOC = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
       '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
       '<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>Lease</w:t></w:r></w:p>'
       '<w:p><w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">2. Rent. </w:t></w:r>'
       '<w:r><w:t xml:space="preserve">Base rent is $2,150 per month, increasing by 5% on each anniversary.</w:t></w:r></w:p>'
       '<w:p><w:r><w:t>Untouched clause stays exactly the same.</w:t></w:r></w:p>'
       '<w:sectPr/></w:body></w:document>')


def make_docx(path):
    parts = redline._minimal_docx([])
    parts["word/document.xml"] = DOC
    parts["word/settings.xml"] = '<?xml version="1.0"?><w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"></w:settings>'
    with zipfile.ZipFile(path, "w") as z:
        for n, d in parts.items():
            z.writestr(n, d)


class Redline(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.src = self.d / "lease.docx"
        make_docx(self.src)

    def run_changes(self, changes):
        out = self.d / "out.docx"
        r = redline.redline(self.src, changes, out)
        z = zipfile.ZipFile(out)
        return r, z.read("word/document.xml").decode(), z

    def test_tracked_change_keeps_formatting_and_untouched_paragraphs(self):
        r, doc, z = self.run_changes([{"find": "increasing by 5% on each anniversary",
                                       "replace": "increasing by the lesser of 3% or CPI", "comment": "Cap the increase."}])
        self.assertEqual((r["applied"], r["comments"], r["not_found"]), (1, 1, []))
        minidom.parseString(doc)
        minidom.parseString(z.read("word/comments.xml"))
        self.assertIn('<w:delText xml:space="preserve">increasing by 5% on each anniversary</w:delText>', doc)
        self.assertIn("increasing by the lesser of 3% or CPI", doc)
        self.assertIn('<w:rPr><w:b/></w:rPr><w:t xml:space="preserve">2. Rent. </w:t>', doc)   # bold heading kept
        self.assertIn("<w:p><w:r><w:t>Untouched clause stays exactly the same.</w:t></w:r></w:p>", doc)  # byte-identical
        self.assertIn("comments.xml", z.read("word/_rels/document.xml.rels").decode())
        self.assertIn("<w:trackRevisions/>", z.read("word/settings.xml").decode())
        self.assertEqual(redline.docx_text(self.d / "out.docx").splitlines()[1],
                         "2. Rent. Base rent is $2,150 per month, increasing by the lesser of 3% or CPI.")

    def test_curly_quotes_and_spacing_still_match(self):
        r, doc, _ = self.run_changes([{"find": "Base  rent is $2,150 per month,", "replace": "Base rent is $2,000 per month,"}])
        self.assertEqual(r["applied"], 1)

    def test_missing_text_is_reported_not_guessed(self):
        r, doc, _ = self.run_changes([{"find": "personal guarantee", "replace": "none"}])
        self.assertEqual((r["applied"], r["not_found"]), (0, ["personal guarantee"]))
        self.assertNotIn("<w:ins", doc)

    def test_plain_text_contract(self):
        t = self.d / "nda.txt"
        t.write_text("Mutual NDA\nThis Agreement lasts forever.\n")
        r = redline.redline(t, [{"find": "lasts forever", "replace": "lasts three (3) years", "comment": "Normal is 2 to 5 years."}], self.d / "nda.docx")
        self.assertEqual(r["applied"], 1)


if __name__ == "__main__":
    unittest.main()
