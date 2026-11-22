"""Mirror the two live essays and extract their lab data, so this companion repeats them exactly and adds no claims.

    python3 scripts/sync.py [--today YYYY-MM-DD] [--from-dir DIR]

Reads https://power.scalingefficiency.com/ ("Who Would Own God?") and https://fix.agireadiness.com/ ("The People
Inside"), or saved copies in --from-dir. Extracts the LABS, ORGS and FIXES data, the "pitch vs charter" items, the
ownership statistics and the numbered references, validates them, and writes:

  data/essays.json        the structured content every companion page is built from
  archive/<essay>.html    the essays exactly as served (published as noindex copies)
  data/live-status.json   when each essay was last fetched and a fingerprint of its text

If an essay cannot be fetched or no longer parses into six labs with every field, nothing is written and an alert is
raised: the companion keeps showing the last good copy. If the live text changed and parses, the companion follows it.
"""
import argparse
import datetime
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from report import add_alert, save_step  # noqa: E402

REPO_URL = "https://github.com/theguysaccount/agi-lab-power-maps"
UA = "agi-lab-power-maps/1.0 (+%s)" % REPO_URL
ESSAYS = {
    "power-map": {"url": "https://power.scalingefficiency.com/", "title": "Who Would Own God? Mapping Power at the AGI Labs"},
    "the-people-inside": {"url": "https://fix.agireadiness.com/", "title": "The People Inside: A Letter to the Engineers Building the Machine"},
}
LABS = ("OpenAI", "Anthropic", "Google DeepMind", "Meta", "xAI", "DeepSeek")


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def js_literal(text):
    """Convert a JavaScript array/object literal of plain data (unquoted keys, double-quoted strings) to Python.

    Never evaluates code: keys are quoted by a small tokenizer and the result is parsed as JSON.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif ch.isalpha() or ch == "_":
            j = i
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word = text[i:j]
            k = j
            while k < n and text[k] in " \t\r\n":
                k += 1
            if k < n and text[k] == ":":
                out.append(json.dumps(word))
            elif word in ("true", "false", "null"):
                out.append(word)
            else:
                raise ValueError("unexpected identifier %r in data literal" % word)
            i = j
        else:
            out.append(ch)
            i += 1
    cleaned = re.sub(r",(\s*[\]}])", r"\1", "".join(out))   # trailing commas are legal in JS, not in JSON
    return json.loads(cleaned)


def array(markup, name):
    m = re.search(r"const %s\s*=\s*\[" % name, markup)
    if not m:
        raise ValueError("no %s data in the page" % name)
    start = m.end() - 1
    depth, i, in_str = 0, start, False
    while i < len(markup):
        c = markup[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
            if depth == 0:
                return js_literal(markup[start:i + 1])
        i += 1
    raise ValueError("unterminated %s" % name)


def text_of(fragment):
    s = re.sub(r"(?is)<(script|style|svg)\b.*?</\1>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", s))).strip()


def pitches(markup):
    """The four 'The Pitch vs The Charter' items: subject, pitch, what the record says, reference numbers."""
    items = []
    body = text_of(markup)
    for m in re.finditer(r"THE PITCH\s+\"(.+?)\"\s+(.+?)\s+SUBJECT\s+·\s+([A-Za-z /,0-9]+?)(?=\s+THE PITCH|\s+The Power Map)", body):
        record = m.group(2)
        refs = re.findall(r"\[(\d+)\]", record)
        items.append({"pitch": m.group(1), "record": re.sub(r"\s*\[\d+\]", "", record).strip(), "refs": refs,
                      "subject": m.group(3).strip()})
    return items


def stats(markup):
    body = text_of(markup)
    out = []
    for m in re.finditer(r"(~?[\d.]+%(?:\s*→\s*[\d.]+%)?)\s+([A-Za-z]+):\s+(.+?)\s+\[(\d+)\]", body):
        out.append({"value": m.group(1), "lab": m.group(2), "text": m.group(3).strip(), "ref": m.group(4)})
    return out


def references(markup):
    """The numbered source list: <li id="rN"><span>label</span> cite · cite</li>, plus the 'as of' caveat above it."""
    m = re.search(r'(?is)<section id="refs".*?</section>', markup)
    if not m:
        raise ValueError("no reference list")
    section = m.group(0)
    intro = text_of((re.search(r"(?is)<p[^>]*>(.*?)</p>", section) or re.match("()", "")).group(1))
    parts = re.split(r"(?<=\.)\s+(?=Concentration)", intro)
    refs = []
    for n, label, rest in re.findall(r'(?is)<li id="r(\d+)">\s*<span>(.*?)</span>(.*?)</li>', section):
        cites = [c.strip() for c in text_of(rest).split("·") if c.strip()]
        refs.append({"n": n, "label": text_of(label),
                     "cites": [{"text": c, "url": "https://" + c, "linked": "/" in c} for c in cites]})
    return {"asOf": parts[0] if parts else intro, "caveat": parts[1] if len(parts) > 1 else "", "refs": refs}


def validate(content):
    problems = []
    names = [lab["nm"] for lab in content["labs"]]
    matches = lambda found: len(found) == len(LABS) and all(any(n.startswith(x) for n in found) for x in LABS)  # noqa: E731
    if not matches(names):
        problems.append("labs are %s" % names)
    for lab in content["labs"]:
        for key in ("nm", "loc", "badge", "conc", "rows", "who", "chain", "chainSub"):
            if key not in lab:
                problems.append("%s lacks %s" % (lab.get("nm"), key))
        if not isinstance(lab.get("conc"), (int, float)) or not 0 <= lab["conc"] <= 100:
            problems.append("%s concentration %r" % (lab.get("nm"), lab.get("conc")))
    if not matches([o["nm"] for o in content["orgs"]]):
        problems.append("ORGS labs are %s" % [o["nm"] for o in content["orgs"]])
    if len(content["references"]["refs"]) < 5:
        problems.append("only %d references" % len(content["references"]["refs"]))
    numbers = {r["n"] for r in content["references"]["refs"]}
    for o in content["orgs"]:
        if str(o.get("ref")) not in numbers:
            problems.append("%s cites missing reference %s" % (o["nm"], o.get("ref")))
    return problems


def extract(power, fix):
    labs = array(power, "LABS")
    for lab in labs:
        lab["slug"] = slug(lab["nm"])
    content = {"labs": labs, "orgs": array(fix, "ORGS"), "fixes": array(fix, "FIXES"), "pitches": pitches(fix),
               "stats": stats(fix), "references": references(fix)}
    built = re.search(r"Built for ([^·<]+?) · ([^·<]+?) · ([A-Z][a-z]+ \d{4})", text_of(power))
    content["published"] = {"by": built.group(2).strip() if built else "", "date": built.group(3) if built else ""}
    return content


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"))
    ap.add_argument("--from-dir")
    args = ap.parse_args(argv)
    pages = {}
    try:
        for key, essay in ESSAYS.items():
            if args.from_dir:
                pages[key] = open(os.path.join(args.from_dir, key + ".html"), encoding="utf-8").read()
            else:
                pages[key] = fetch(essay["url"])
        content = extract(pages["power-map"], pages["the-people-inside"])
        problems = validate(content)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        content, problems = None, ["%s: %s" % (type(exc).__name__, exc)]
    status_path = os.path.join(ROOT, "data", "live-status.json")
    status = json.load(open(status_path)) if os.path.exists(status_path) else {}
    if problems:
        status.update({"lastAttempt": args.today, "lastProblem": "; ".join(problems)[:500]})
        json.dump(status, open(status_path, "w"), indent=1)
        add_alert("essay-sync", "The live essays could not be mirrored",
                  "On %s: %s. The companion keeps the last good copy (synced %s)." % (args.today, "; ".join(problems)[:800], status.get("synced", "never")))
        save_step("sync", False, "essay sync failed: %s" % "; ".join(problems)[:200])
        print("sync failed:", problems)
        return 1
    fingerprints = {k: hashlib.sha256(text_of(v).encode()).hexdigest() for k, v in pages.items()}
    old_path = os.path.join(ROOT, "data", "essays.json")
    old = json.load(open(old_path, encoding="utf-8")) if os.path.exists(old_path) else None
    changed = old is None or {k: v for k, v in old.items() if k != "synced"} != content
    content["synced"] = args.today if changed else old.get("synced", args.today)
    os.makedirs(os.path.join(ROOT, "archive"), exist_ok=True)
    for key, markup in pages.items():
        with open(os.path.join(ROOT, "archive", key + ".html"), "w", encoding="utf-8") as fh:
            fh.write(markup)
    with open(old_path, "w", encoding="utf-8") as fh:
        json.dump(content, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    status = {"checked": args.today, "synced": content["synced"], "fingerprints": fingerprints,
              "essays": {k: v["url"] for k, v in ESSAYS.items()}}
    json.dump(status, open(status_path, "w"), indent=1)
    if changed and old is not None:
        add_alert("essay-changed", "The live essays changed; the companion followed them",
                  "On %s the live essays' lab data changed, and the lab pages were rebuilt from the new text. Review the "
                  "diff of data/essays.json in this commit to confirm the new claims are sourced." % args.today)
    save_step("sync", True, "essays: %s" % ("changed, re-synced" if changed else "unchanged"))
    print("essays", "changed" if changed else "unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
