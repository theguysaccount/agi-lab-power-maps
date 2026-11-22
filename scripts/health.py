"""Weekly self-test of the live companion: pages answer, lab pages still match the essays' data, indexing per page type,
and the weekly sync and link check are fresh (dispatches weekly.yml when they are not).

    python3 scripts/health.py [base_url]
"""
import datetime
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

UA = "agi-lab-power-maps-selftest/1.0 (+https://github.com/theguysaccount/agi-lab-power-maps)"


def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            return exc.code, ""
        except Exception as exc:
            last = str(exc)
        time.sleep(3 * (i + 1))
    return 0, last


def main(base):
    base = base.rstrip("/")
    lines, failed, stale = ["## Live companion", ""], False, False

    def ok(good, text):
        nonlocal failed
        lines.append("- %s %s" % ("ok  " if good else "FAIL", text))
        failed |= not good

    b = "?selftest=%d" % int(time.time())
    st, raw = get(base + "/data/essays.json" + b)
    try:
        content = json.loads(raw)
        ok(len(content["labs"]) == 6, "essays.json: %d labs, synced %s" % (len(content["labs"]), content.get("synced")))
    except Exception as exc:
        content = None
        ok(False, "essays.json: %s" % exc)
    noindex = lambda h: 'name="robots" content="noindex"' in h  # noqa: E731
    for p in ("/", "/method/", "/sources/"):
        st, body = get(base + p + b)
        ok(st == 200 and not noindex(body), "%s answers and is indexable" % p)
    for key, live in (("power-map", "https://power.scalingefficiency.com/"), ("the-people-inside", "https://fix.agireadiness.com/")):
        st, body = get(base + "/essays/%s/" % key + b)
        ok(st == 200 and noindex(body) and ('<link rel="canonical" href="%s">' % live) in body, "archive %s is noindex, canonical to the live essay" % key)
    if content:
        for lab in content["labs"]:
            st, body = get(base + "/labs/%s/" % lab["slug"] + b)
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))
            who = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", lab["who"]))
            import html as _h
            ok(st == 200 and who in _h.unescape(text) and 'class="verify' in body, "labs/%s matches the essays" % lab["slug"])
    st, sm = get(base + "/sitemap.xml" + b)
    ok(st == 200 and "/labs/" in sm and "/essays/" not in sm, "sitemap lists the lab pages and not the archives")
    today = datetime.date.today()
    for name, field in (("essays.json", "synced"), ("link-health.json", "checked")):
        st, raw = get(base + "/data/" + name + b)
        try:
            data = json.loads(raw)
            when = data.get("checked") or data.get(field)
            age = (today - datetime.date.fromisoformat(when)).days
        except Exception:
            age = 10 ** 6
        if name == "essays.json":
            continue   # 'synced' only moves when the essays change; freshness of the sync itself is in live-status
        if age > 30:
            ok(False, "%s is %s days old" % (name, age))
            stale = True
        elif age > 15:
            stale = True
            lines.append("- warn %s is %d days old" % (name, age))
        else:
            lines.append("- ok   %s checked %d days ago" % (name, age))
    if stale and os.environ.get("GH_TOKEN"):
        r = subprocess.run(["gh", "workflow", "run", "weekly.yml", "-R", os.environ.get("GITHUB_REPOSITORY", ""), "--ref", "main"], capture_output=True, text=True)
        lines.append("- dispatched weekly.yml: %s" % ("ok" if r.returncode == 0 else r.stderr.strip()[:120]))
    text = "\n".join(lines)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(text + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SITE_URL") or "https://theguysaccount.github.io/agi-lab-power-maps"))
