"""Extraction from the essays: data literals parse without evaluating code, and validation catches broken pages."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import sync  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")


class Literal(unittest.TestCase):
    def test_plain_data(self):
        self.assertEqual(sync.js_literal('[{nm:"A",conc:42,rows:[["K","v: with colon"]],ok:true,},]'),
                         [{"nm": "A", "conc": 42, "rows": [["K", "v: with colon"]], "ok": True}])

    def test_escaped_quotes_survive(self):
        self.assertEqual(sync.js_literal('[{d:"say \\"no\\" twice"}]'), [{"d": 'say "no" twice'}])

    def test_code_is_refused(self):
        with self.assertRaises(ValueError):
            sync.js_literal('[{nm:alert(1)}]')


class Essays(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        power = open(os.path.join(FIX, "power-map.html"), encoding="utf-8").read()
        fix = open(os.path.join(FIX, "the-people-inside.html"), encoding="utf-8").read()
        cls.content = sync.extract(power, fix)

    def test_six_labs_with_every_field(self):
        self.assertEqual(sync.validate(self.content), [])

    def test_references_are_numbered_and_resolvable(self):
        refs = self.content["references"]["refs"]
        self.assertEqual([r["n"] for r in refs], [str(i) for i in range(1, len(refs) + 1)])
        for r in refs:
            self.assertTrue(r["label"])
            for c in r["cites"]:
                self.assertTrue(c["url"].startswith("https://"))

    def test_pitches_and_stats_carry_reference_numbers(self):
        numbers = {r["n"] for r in self.content["references"]["refs"]}
        self.assertTrue(self.content["pitches"])
        for p in self.content["pitches"]:
            self.assertTrue(set(p["refs"]) <= numbers, p)
        for s in self.content["stats"]:
            self.assertIn(s["ref"], numbers)

    def test_validation_catches_a_missing_lab(self):
        broken = json.loads(json.dumps(self.content))
        broken["labs"] = broken["labs"][:5]
        self.assertTrue(sync.validate(broken))

    def test_validation_catches_a_bad_score(self):
        broken = json.loads(json.dumps(self.content))
        broken["labs"][0]["conc"] = 140
        self.assertTrue(sync.validate(broken))


if __name__ == "__main__":
    unittest.main()
