"""Weekly check of every linked source the essays cite. Writes data/link-health.json.

    python3 scripts/linkcheck.py [--today YYYY-MM-DD]

Citations that name only an outlet ("cnbc.com") are not fetched: the essay gives no article to check. A site that
refuses scripts (401/403/405/429) counts as "blocked", not broken. A link is reported only after failing on two runs.
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from report import add_alert, save_step  # noqa: E402

UA = "agi-lab-power-maps-linkcheck/1.0 (+https://github.com/theguysaccount/agi-lab-power-maps)"
BOT_WALLS = (401, 403, 405, 406, 429, 451)


def classify(status, error=""):
    if 200 <= status < 400:
        return "ok"
    if status in BOT_WALLS:
        return "blocked"
    if status == 0 and not any(m in error.lower() for m in ("name or service", "nodename", "getaddrinfo", "no address")):
        return "unreachable"
    return "broken"


def probe(url):
    for attempt in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                return r.status, ""
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504):
                return exc.code, ""
            last = (exc.code, "")
        except Exception as exc:
            last = (0, str(exc)[:120])
        time.sleep(4)
    return last


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"))
    args = ap.parse_args(argv)
    content = json.load(open(os.path.join(ROOT, "data", "essays.json"), encoding="utf-8"))
    path = os.path.join(ROOT, "data", "link-health.json")
    prev = json.load(open(path)) if os.path.exists(path) else {"results": {}}
    results = {}
    for ref in content["references"]["refs"]:
        for c in ref["cites"]:
            if not c["linked"] or c["url"] in results:
                continue
            status, error = probe(c["url"])
            st = classify(status, error)
            old = prev["results"].get(c["url"], {})
            since = None
            if st in ("broken", "unreachable"):
                since = old.get("since") if old.get("status") in ("broken", "unreachable") else args.today
            results[c["url"]] = {"status": st, "http": status, "error": error, "since": since, "refs": [ref["n"]]}
            time.sleep(1.5)
    if results and not any(r["status"] in ("ok", "blocked") for r in results.values()):
        save_step("links", False, "no source link answered at all; previous report kept")
        print("no link answered; keeping the previous report")
        return 1
    with open(path, "w") as fh:
        json.dump({"checked": args.today, "results": results}, fh, indent=1)
        fh.write("\n")
    stale = [(u, r) for u, r in results.items() if r["since"] and r["since"] < args.today]
    if stale:
        add_alert("source-links", "%d cited source link(s) failing" % len(stale),
                  "These links cited by the essays have failed on separate weekly checks:\n\n" + "\n".join(
                      "- %s (%s, %s, since %s), reference [%s]" % (u, r["status"], r["http"] or r["error"], r["since"], ", ".join(r["refs"])) for u, r in stale)
                  + "\n\nThe essays' authors should replace them with current sources; this site copies whatever the live essays cite.")
    counts = {}
    for r in results.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    save_step("links", True, "source links: %s" % ", ".join("%d %s" % (v, k) for k, v in sorted(counts.items())))
    print(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
