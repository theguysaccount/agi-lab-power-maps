"""The companion adds no claims: every lab page repeats the essays verbatim, cites sources and shows its review state."""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "site"))
import build  # noqa: E402


class Site(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.cfg, cls.content, cls.pages = build.build(os.path.join(cls.tmp, "d"), env={"SITE_URL": "https://example.org/agi", "BUILD_DATE": "2026-11-22"})

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def read(self, rel):
        return open(os.path.join(self.tmp, "d", rel), encoding="utf-8").read()

    def text(self, rel):
        return re.sub(r"\s+", " ", build.html.unescape(re.sub(r"<[^>]+>", " ", self.read(rel))))

    def test_lab_pages_repeat_the_essays_verbatim(self):
        for lab in self.content["labs"]:
            t = self.text("labs/%s/index.html" % lab["slug"])
            self.assertIn(re.sub(r"\s+", " ", build.plain(lab["who"])), t)
            for step in lab["chain"]:
                self.assertIn(step["d"], t)
            for k, v in lab["rows"]:
                self.assertIn(v, t)

    def test_every_lab_page_has_sources_and_a_review_box(self):
        for lab in self.content["labs"]:
            html = self.read("labs/%s/index.html" % lab["slug"])
            self.assertRegex(html, r'<ol class="sources"><li id="r\d+">')
            self.assertIn('class="verify', html)
            self.assertIn("editorial", html)

    def test_review_due_follows_the_date_not_a_constant(self):
        fresh = build.Cfg({"BUILD_DATE": "2026-06-01"})
        old = build.Cfg({"BUILD_DATE": "2027-06-01"})
        content = dict(self.content, published={"by": "x", "date": "May 2026"})
        self.assertEqual(build.review_state(content, fresh)[0], "ok")
        self.assertEqual(build.review_state(content, old)[0], "due")

    def test_archives_are_noindex_copies_pointing_at_the_live_essays(self):
        for key, (url, _) in build.ESSAYS.items():
            html = self.read("essays/%s/index.html" % key)
            self.assertIn('<meta name="robots" content="noindex">', html)
            self.assertIn('<link rel="canonical" href="%s">' % url, html)
            self.assertEqual(len(re.findall(r'rel="canonical"', html)), 1)

    def test_sitemap_lists_only_the_new_pages(self):
        locs = re.findall(r"<loc>(.*?)</loc>", self.read("sitemap.xml"))
        self.assertIn("https://example.org/agi/", locs)
        self.assertEqual(len([l for l in locs if "/labs/" in l]), len(self.content["labs"]))
        self.assertFalse([l for l in locs if "/essays/" in l])

    def test_lawful_channels_and_disclosure_on_the_method_page(self):
        t = self.text("method/index.html")
        self.assertIn("does not ask anyone to breach", t)
        self.assertIn("Orgoneism", t)


if __name__ == "__main__":
    unittest.main()
