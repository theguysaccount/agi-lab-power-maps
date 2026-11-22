"""Build the static companion to the AGI power-map essays into dist/.

    python3 site/build.py [--out dist]

Every lab fact on these pages is copied from data/essays.json, which scripts/sync.py extracts verbatim from the live
essays. This builder adds structure (one page per lab), sources, dates and link status, never claims.

Settings (environment, optional): SITE_URL, SITE_REPO, REVIEW_AGE_DAYS (default 180), GOATCOUNTER_URL, SUPPORT_URL,
SUPPORT_LABEL, BUILD_DATE.
"""
import argparse
import datetime
import html
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
ESSAYS = {"power-map": ("https://power.scalingefficiency.com/", "Who Would Own God? Mapping Power at the AGI Labs"),
          "the-people-inside": ("https://fix.agireadiness.com/", "The People Inside: A Letter to the Engineers Building the Machine")}
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
KEYWORD = {"openai": "openai", "anthropic": "anthropic", "google-deepmind": "deepmind", "meta-superintelligence-labs": "meta",
           "xai": "xai", "deepseek": "deepseek"}


def e(v):
    return html.escape("" if v is None else str(v), quote=True)


def rich(v):
    """The essays use <b> for emphasis inside a few strings: keep that, escape everything else."""
    return re.sub(r"&lt;(/?)b&gt;", r"<\1b>", e(v))


def plain(v):
    return re.sub(r"<[^>]+>", "", str(v or ""))


def long_date(iso):
    if not iso:
        return ""
    y, m, d = iso[:10].split("-")
    return "%d %s %s" % (int(d), MONTHS[int(m) - 1], y)


def month_start(label):
    """'May 2026' -> date(2026, 5, 1); None if unparseable."""
    m = re.match(r"([A-Z][a-z]+) (\d{4})$", (label or "").strip())
    if not m or m.group(1) not in MONTHS:
        return None
    return datetime.date(int(m.group(2)), MONTHS.index(m.group(1)) + 1, 1)


class Cfg(object):
    def __init__(self, env):
        self.url = (env.get("SITE_URL") or "https://theguysaccount.github.io/agi-lab-power-maps").rstrip("/")
        self.repo = env.get("SITE_REPO") or "theguysaccount/agi-lab-power-maps"
        self.repo_url = "https://github.com/" + self.repo
        self.review_age = int(env.get("REVIEW_AGE_DAYS") or 180)
        self.goatcounter = (env.get("GOATCOUNTER_URL") or "").strip()
        self.support_url = (env.get("SUPPORT_URL") or "").strip()
        self.support_label = (env.get("SUPPORT_LABEL") or "Support this project").strip()
        self.built = env.get("BUILD_DATE") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def lab_refs(content, lab):
    """Reference numbers the essays attach to this lab: its ORGS entry, its pitch items and statistics, and the
    references whose own label names it."""
    key = KEYWORD.get(lab["slug"], lab["slug"])
    norm = lambda s: re.sub(r"[^a-z]", "", s.lower())  # noqa: E731
    refs = []
    org = org_for(content, lab)
    if org and org.get("ref"):
        refs.append(str(org["ref"]))
    for p in content["pitches"]:
        if key in norm(p["subject"]):
            refs += p["refs"]
    for s in content["stats"]:
        if key == norm(s["lab"]):
            refs.append(s["ref"])
    for r in content["references"]["refs"]:
        if key in norm(r["label"]):
            refs.append(r["n"])
    seen = []
    for r in refs:
        if r not in seen:
            seen.append(r)
    return sorted(seen, key=int)


def org_for(content, lab):
    return next((o for o in content["orgs"] if o["nm"] == lab["nm"]), None)


def fixes_for(content, lab):
    return next((f for f in content["fixes"] if f["nm"] == lab["nm"]), None)


def review_state(content, cfg):
    """('due'|'ok', text). The essays state their facts are 'as of late 2025 / early 2026' and were published in a
    month; past REVIEW_AGE_DAYS from publication, every lab page says a review is due."""
    published = month_start(content["published"].get("date"))
    today = datetime.date.fromisoformat(cfg.built)
    if not published:
        return "due", "The essays do not state a publication date; treat these facts as unreviewed."
    age = (today - published).days
    text = ("The essays were published in %s and state their governance and ownership facts as of late 2025 / early 2026."
            % content["published"]["date"])
    if age > cfg.review_age:
        return "due", text + " That is more than %d months ago, so a review against current sources is due; boards, stakes and structures may have changed." % (cfg.review_age // 30)
    return "ok", text


# ---------------------------------------------------------------- page shell

def page(cfg, content, rel, title, desc, body, depth, index=True, og="og/default.png", canonical=None, ld=None):
    root = "../" * depth
    robots = "" if index else '<meta name="robots" content="noindex">\n'
    gc = ('<script data-goatcounter="%s" async src="https://gc.zgo.at/count.js"></script>\n' % e(cfg.goatcounter)) if cfg.goatcounter else ""
    support = ('<p><a href="%s" rel="noopener">%s</a></p>' % (e(cfg.support_url), e(cfg.support_label))) if cfg.support_url else ""
    ld_html = "".join('<script type="application/ld+json">%s</script>\n' % json.dumps(x, ensure_ascii=False).replace("</", "<\\/") for x in (ld or []))
    labs_nav = "".join('<a href="%slabs/%s/">%s</a>' % (root, e(l["slug"]), e(short(l["nm"]))) for l in content["labs"])
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
{robots}<link rel="canonical" href="{canon}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="AGI Lab Power Maps">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{self_url}">
<meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{root}assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{root}assets/style.css">
{ld}{gc}</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><a class="brand" href="{root}">◢ AGI Lab Power Maps</a><nav aria-label="Labs">{labs_nav}</nav></header>
<main id="main">
{body}
</main>
<footer class="foot">
<p>Every lab fact here is copied from two visual essays, <a href="{e1}">Who Would Own God?</a> and <a href="{e2}">The People Inside</a>,
published by {by} in {date}, with the sources they cite. This site adds the per-lab layout, dates and link checks, and no claims of its own.
Concentration scores are the essays' editorial reading, not measurements. <a href="{root}method/">Method and disclosure</a> &middot;
<a href="{root}sources/">Sources</a> &middot; <a href="{repo}/issues/new?template=correction.yml">Report an error</a> &middot; built {built}</p>
{support}
</footer>
<script type="module" src="{root}assets/site.js"></script>
</body>
</html>
""".format(title=e(title), desc=e(desc), robots=robots, canon=e(canonical or cfg.url + "/" + rel), self_url=e(cfg.url + "/" + rel),
           og=e(cfg.url + "/" + og), root=root, ld=ld_html, gc=gc, labs_nav=labs_nav, body=body, e1=e(ESSAYS["power-map"][0]),
           e2=e(ESSAYS["the-people-inside"][0]), by=e(content["published"].get("by") or "their authors"),
           date=e(content["published"].get("date") or "2026"), repo=e(cfg.repo_url), built=e(long_date(cfg.built)), support=support)


def short(name):
    return {"Meta Superintelligence Labs": "Meta", "Google DeepMind": "DeepMind"}.get(name, name)


def ref_links(nums, root):
    return " ".join('<a class="ref" href="%ssources/#r%s">[%s]</a>' % (root, e(n), e(n)) for n in nums)


def verification(cfg, content, links, refs, root):
    state, text = review_state(content, cfg)
    checked = (links or {}).get("checked")
    counts = {"ok": 0, "blocked": 0, "broken": 0, "unreachable": 0, "unlinked": 0}
    for r in content["references"]["refs"]:
        if r["n"] not in refs:
            continue
        for c in r["cites"]:
            st = "unlinked" if not c["linked"] else (links or {}).get("results", {}).get(c["url"], {}).get("status", "unchecked")
            counts[st] = counts.get(st, 0) + 1
    link_line = ("Cited links last checked %s: %d answer, %d refuse scripts, %d broken or silent; %d citations name an outlet "
                 "without the article." % (long_date(checked), counts["ok"], counts["blocked"], counts["broken"] + counts["unreachable"], counts["unlinked"])
                 if checked else "Cited links not checked yet.")
    return ('<aside class="verify verify-%s" data-review="%s"><b>Last verified</b><p>%s</p><p>Copied from the live essays on %s. %s</p></aside>'
            % (state, state, e(text), e(long_date(content.get("synced"))), e(link_line)))


# ---------------------------------------------------------------- pages

def lab_page(cfg, content, links, lab):
    root = "../../"
    refs = lab_refs(content, lab)
    org = org_for(content, lab) or {}
    fx = fixes_for(content, lab)
    key = KEYWORD.get(lab["slug"], lab["slug"])
    norm = lambda s: re.sub(r"[^a-z]", "", s.lower())  # noqa: E731
    pitches = [p for p in content["pitches"] if key in norm(p["subject"])]
    stats = [s for s in content["stats"] if norm(s["lab"]) == key]
    rows = "".join("<tr><th scope=\"row\">%s</th><td>%s</td></tr>" % (e(k.title()), e(v)) for k, v in lab["rows"])
    chain = "".join('<li><span class="role">%s</span><b>%s</b><p>%s</p></li>' % (e(c["role"]), e(c["who"]), e(c["d"])) for c in lab["chain"])
    pitch_html = "".join('<blockquote class="pitch"><p class="said">They say: &ldquo;%s&rdquo;</p><p>%s %s</p></blockquote>'
                         % (e(p["pitch"]), e(p["record"]), ref_links(p["refs"], root)) for p in pitches)
    stat_html = "".join('<p class="stat"><b>%s</b> %s %s</p>' % (e(s["value"]), e(s["text"]), ref_links([s["ref"]], root)) for s in stats)
    fix_html = ""
    if fx:
        fix_html = ('<h2>The essay\'s proposed fixes</h2><p class="muted">A prescription from "The People Inside", not a fact about %s and not '
                    'something the lab has agreed to.</p><p><b>%s</b> %s</p><ol class="fixes">%s</ol>'
                    % (e(lab["nm"]), e(fx.get("tag", "")), e(fx.get("why", "")),
                       "".join("<li><b>%s</b> %s</li>" % (e(s[0]), e(s[1])) for s in fx.get("steps", []))))
    src = "".join('<li id="r%s"><b>[%s]</b> %s %s</li>' % (e(r["n"]), e(r["n"]), e(r["label"]), cite_list(r, links))
                  for r in content["references"]["refs"] if r["n"] in refs)
    body = """
<article class="lab" data-lab="{slug}">
<p class="kicker">{loc} &middot; {badge}</p>
<h1>Who controls {name}?</h1>
<p class="lede"><span class="lbl">{who_lbl}</span> {who}</p>
<p>{chain_sub}</p>
{verify}
<div class="score"><span class="num">{conc}</span><span class="of">/100</span><span class="what">concentration of ultimate control, the essays' editorial
reading (0 = structurally checked, 100 = one person decides). <a href="../../method/">How to read it</a></span></div>
<h2>Chain of command</h2>
<ol class="chain">{chain}</ol>
<h2>At a glance</h2>
<table class="facts">{rows}<tr><th scope="row">Workforce</th><td>{hc} {hc_ref}</td></tr></table>
{fact}
{stats}
{pitch_block}
{fix}
<h2>Sources the essays cite for {name}</h2>
<ol class="sources">{src}</ol>
<p class="muted">Read the full essays: <a href="{e1}">Who Would Own God?</a> &middot; <a href="{e2}">The People Inside</a>.</p>
</article>""".format(
        slug=e(lab["slug"]), loc=e(lab["loc"]), badge=e(lab["badge"]), name=e(lab["nm"]), who_lbl=e(lab.get("whoLbl", "Ultimate control")),
        who=rich(lab["who"]), chain_sub=e(lab["chainSub"]), verify=verification(cfg, content, links, refs, root), conc=e(lab["conc"]),
        chain=chain, rows=rows, hc=e(org.get("hc", "not stated")),
        hc_ref=ref_links(["10"], root) if any(r["n"] == "10" and KEYWORD.get(lab["slug"], "") in norm(r["label"]) for r in content["references"]["refs"]) else "",
        fact=('<p><b>%s:</b> %s. %s %s</p>' % (e(org.get("ctrlL", "")).capitalize(), e(org.get("ctrl", "")), e(org.get("fact", "")),
                                                 ref_links([str(org["ref"])], root)) if org else ""),
        stats=stat_html, pitch_block=("<h2>The pitch and the record</h2>" + pitch_html) if pitch_html else "", fix=fix_html, src=src,
        e1=e(ESSAYS["power-map"][0]), e2=e(ESSAYS["the-people-inside"][0]))
    title = "Who controls %s? Chain of command, board and ownership" % lab["nm"]
    desc = "%s: %s. Concentration %s/100 (editorial). Every fact sourced, with the date it was last verified." % (lab["nm"], plain(lab["who"]), lab["conc"])
    ld = [{"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc,
           "dateModified": content.get("synced"), "url": cfg.url + "/labs/%s/" % lab["slug"],
           "about": {"@type": "Organization", "name": lab["nm"]},
           "citation": [c["url"] for r in content["references"]["refs"] if r["n"] in refs for c in r["cites"] if c["linked"]],
           "isBasedOn": [ESSAYS["power-map"][0], ESSAYS["the-people-inside"][0]]}]
    return page(cfg, content, "labs/%s/" % lab["slug"], title, desc, body, 2, og="og/%s.png" % lab["slug"], ld=ld)


def cite_list(r, links):
    out = []
    for c in r["cites"]:
        if not c["linked"]:
            out.append('<span class="cite unlinked" title="The essay names the outlet but not the article">%s</span>' % e(c["text"]))
            continue
        st = (links or {}).get("results", {}).get(c["url"], {}).get("status", "unchecked")
        out.append('<a class="cite cite-%s" href="%s" rel="noopener">%s</a>' % (e(st), e(c["url"]), e(c["text"])))
    return " &middot; ".join(out)


def home_page(cfg, content, links):
    cards = "".join("""<a class="card" href="labs/{slug}/"><span class="kicker">{badge}</span><b>{name}</b>
<span class="who">{who}</span><span class="conc"><i style="width:{conc}%"></i></span><span class="muted">{conc}/100 concentration (editorial)</span></a>""".format(
        slug=e(l["slug"]), badge=e(l["badge"]), name=e(l["nm"]), who=e(plain(l["who"])), conc=e(l["conc"])) for l in content["labs"])
    state, text = review_state(content, cfg)
    body = """
<section class="intro">
<p class="kicker">Six labs &middot; one question</p>
<h1>Who controls the AGI labs?</h1>
<p class="lede">Who holds ultimate control at OpenAI, Anthropic, Google DeepMind, Meta, xAI and DeepSeek, through what legal lever, and how
concentrated it is: one page per lab, every fact with its source and the date it was last verified.</p>
<p class="muted">{text}</p>
</section>
<div class="cards">{cards}</div>
<section><h2>Where this comes from</h2>
<p>The mapping is from two visual essays: <a href="{e1}">Who Would Own God?</a>, for the public, and <a href="{e2}">The People Inside</a>, a letter to
lab employees. This site restates their lab-by-lab findings on separate pages, lists the sources they cite and checks those links every week.
It makes no claims of its own. Archived copies of both essays as published: <a href="essays/power-map/">Who Would Own God?</a> &middot;
<a href="essays/the-people-inside/">The People Inside</a>.</p>
<p><a href="method/">How to read the concentration score, and who wrote the essays</a> &middot; <a href="sources/">All sources and their link status</a></p>
</section>""".format(text=e(text), cards=cards, e1=e(ESSAYS["power-map"][0]), e2=e(ESSAYS["the-people-inside"][0]))
    return page(cfg, content, "", "Who controls the AGI labs? OpenAI, Anthropic, DeepMind, Meta, xAI, DeepSeek",
                "Who holds ultimate control at the six frontier AI labs, through what legal lever, and how concentrated it is. Sourced and dated.", body, 0)


def method_page(cfg, content, links):
    labs = "".join("<tr><td><a href=\"../labs/%s/\">%s</a></td><td class=\"num\">%s</td></tr>" % (e(l["slug"]), e(l["nm"]), e(l["conc"])) for l in content["labs"])
    body = """
<h1>Method and disclosure</h1>
<h2>The concentration score</h2>
<p>Each lab carries a score from 0 to 100: <b>0 = structurally checked, 100 = one person decides</b>. The essays describe it as {caveat_lc} They do
not publish a formula, so this site does not invent one: the scores below are exactly as the essays give them.</p>
<table class="facts"><thead><tr><th>Lab</th><th class="num">Score</th></tr></thead><tbody>{labs}</tbody></table>
<h2>Dates</h2>
<p>{as_of} The essays were published in {date}. Each lab page shows this, the date the companion last copied the live essays, and the
date the cited links were last checked. Six months after publication every page says a review is due, because boards, stakes and
structures change.</p>
<h2>What this site does and does not do</h2>
<ul>
<li>It copies the essays' lab findings verbatim from the live pages every week, and follows them if they change.</li>
<li>It adds structure (a page per lab), the numbered sources the essays cite, dates and weekly link checks.</li>
<li>It adds no claims. Where the essays name an outlet without the article (for example "cnbc.com"), the citation is marked as not linked.</li>
<li>It does not solicit confidential documents and does not ask anyone to breach an employment or confidentiality agreement.
People with concerns about a lab can use lawful channels: <a href="https://righttowarn.ai/">the "Right to Warn" principles</a>,
<a href="https://whistlebloweraid.org/">Whistleblower Aid</a> and the <a href="https://whistleblower.org/">Government Accountability Project</a>
offer information and legal support.</li>
</ul>
<h2>Who wrote the essays</h2>
<p>The essays state that they were built for {by} ({date}). They argue that no lab's structure lets humanity decide, and they advocate a
governance model of their own, which they call Orgoneism. The essays are hosted on agireadiness.com and scalingefficiency.com. Read them with
that in mind; this companion reproduces their lab mapping, not their proposal.</p>
<h2>Corrections</h2>
<p>If a fact is wrong or out of date, <a href="{repo}/issues/new?template=correction.yml">open a correction</a> with a source.</p>""".format(
        caveat_lc=e(content["references"]["caveat"][0].lower() + content["references"]["caveat"][1:]) if content["references"]["caveat"] else "",
        labs=labs, as_of=e(content["references"]["asOf"]), date=e(content["published"].get("date") or "2026"),
        by=e(content["published"].get("by") or "their authors"), repo=e(cfg.repo_url))
    return page(cfg, content, "method/", "How to read the AGI lab power maps: concentration scores, dates and sources",
                "What the 0-100 concentration score means, how the lab facts are dated and sourced, and who wrote the essays.", body, 1)


def sources_page(cfg, content, links):
    used = {}
    for lab in content["labs"]:
        for n in lab_refs(content, lab):
            used.setdefault(n, []).append(lab)
    items = "".join('<li id="r%s"><b>[%s]</b> %s<div>%s</div><div class="muted">Used for: %s</div></li>' % (
        e(r["n"]), e(r["n"]), e(r["label"]), cite_list(r, links),
        ", ".join('<a href="../labs/%s/">%s</a>' % (e(l["slug"]), e(short(l["nm"]))) for l in used.get(r["n"], [])) or "the essays' overall figures")
        for r in content["references"]["refs"])
    checked = (links or {}).get("checked")
    body = """
<h1>Sources</h1>
<p class="lede">The numbered sources from "The People Inside", with the status of each link{checked}.</p>
<p class="muted">{as_of} {caveat}</p>
<ol class="sources all">{items}</ol>
<p class="muted">A grey citation names an outlet without the article, as the essay does; it cannot be checked automatically.</p>""".format(
        checked=(" on %s" % e(long_date(checked))) if checked else " (not checked yet)", as_of=e(content["references"]["asOf"]),
        caveat=e(content["references"]["caveat"]), items=items)
    return page(cfg, content, "sources/", "Sources for the AGI lab power maps, with weekly link checks",
                "Every source the AGI power-map essays cite, which lab facts rely on it, and whether its link still answers.", body, 1)


def archive_page(cfg, key, markup, synced):
    """The essay exactly as served, with a noindex tag, the live page as canonical, and a one-line archive note."""
    url, title = ESSAYS[key]
    head_add = '<meta name="robots" content="noindex">\n<link rel="canonical" href="%s">\n' % e(url)
    markup = re.sub(r'(?i)<link rel="canonical"[^>]*>\s*', "", markup)
    markup = re.sub(r"(?i)<meta name=\"robots\"[^>]*>\s*", "", markup)
    markup = re.sub(r"(?i)<head>", "<head>\n" + head_add, markup, count=1)
    note = ('<div style="position:relative;z-index:9999;background:#ffe08a;color:#111;font:14px/1.4 system-ui,sans-serif;padding:8px 14px;text-align:center">'
            'Archived copy as served on %s. The live essay is at <a style="color:#111;font-weight:700" href="%s">%s</a>.</div>' % (e(long_date(synced)), e(url), e(url.replace("https://", "").rstrip("/"))))
    return re.sub(r"(?i)(<body[^>]*>)", r"\1" + note.replace("\\", "\\\\"), markup, count=1)


# ---------------------------------------------------------------- share cards

def og_card(title, line, conc, foot):
    bar = "" if conc is None else '<div class="bar"><i style="width:%s%%"></i></div><div class="c">Concentration %s/100 (editorial)</div>' % (conc, conc)
    return """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:1200px;height:630px;background:#0a0a0f;color:#f4f1ea;font-family:-apple-system,"Segoe UI",Inter,system-ui,sans-serif}}
.w{{box-sizing:border-box;width:1200px;height:630px;padding:64px 72px;display:flex;flex-direction:column;justify-content:space-between;border-top:10px solid #ff4d4d}}
.k{{font:600 22px ui-monospace,Menlo,monospace;letter-spacing:.2em;color:#ff4d4d}}h1{{font-size:68px;line-height:1.04;margin:22px 0 0;font-weight:800;letter-spacing:-.02em}}
.l{{font-size:32px;line-height:1.3;color:#cfc9bd;margin-top:22px}}.bar{{height:16px;background:#2a2a33;border-radius:8px;margin-top:26px;width:900px}}
.bar i{{display:block;height:16px;border-radius:8px;background:#ff4d4d}}.c{{font:500 22px ui-monospace,Menlo,monospace;color:#cfc9bd;margin-top:10px}}
.f{{font:400 22px ui-monospace,Menlo,monospace;color:#8f8a80}}</style></head><body><div class="w"><div><div class="k">◢ AGI LAB POWER MAPS</div>
<h1>{title}</h1><div class="l">{line}</div>{bar}</div><div class="f">{foot}</div></div></body></html>""".format(title=e(title), line=e(line), bar=bar, foot=e(foot))


# ---------------------------------------------------------------- build

def build(out=None, env=None):
    env = os.environ if env is None else env
    cfg = Cfg(env)
    dist = out or os.path.join(ROOT, "dist")
    content = json.load(open(os.path.join(ROOT, "data", "essays.json"), encoding="utf-8"))
    lp = os.path.join(ROOT, "data", "link-health.json")
    links = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else None
    if os.path.exists(dist):
        shutil.rmtree(dist)
    shutil.copytree(os.path.join(SITE, "assets"), os.path.join(dist, "assets"))
    pages = []

    def write(rel, text, indexable=True):
        full = os.path.join(dist, rel, "index.html")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w", encoding="utf-8").write(text)
        if indexable:
            pages.append(rel)

    write("", home_page(cfg, content, links))
    for lab in content["labs"]:
        write("labs/%s/" % lab["slug"], lab_page(cfg, content, links, lab))
    write("method/", method_page(cfg, content, links))
    write("sources/", sources_page(cfg, content, links))
    for key in ESSAYS:
        path = os.path.join(ROOT, "archive", key + ".html")
        if os.path.exists(path):
            write("essays/%s/" % key, archive_page(cfg, key, open(path, encoding="utf-8").read(), content.get("synced")), indexable=False)
    open(os.path.join(dist, "404.html"), "w").write(page(cfg, content, "404.html", "Page not found", "Page not found.",
                                                          '<h1>Page not found</h1><p><a href="%s/">All six labs</a></p>' % e(cfg.url), 0, index=False))
    os.makedirs(os.path.join(dist, "_og"), exist_ok=True)
    host = cfg.url.split("://", 1)[-1]
    open(os.path.join(dist, "_og", "default.html"), "w").write(og_card("Who controls the AGI labs?", "OpenAI · Anthropic · Google DeepMind · Meta · xAI · DeepSeek. Sourced and dated.", None, host))
    for lab in content["labs"]:
        open(os.path.join(dist, "_og", lab["slug"] + ".html"), "w").write(og_card("Who controls %s?" % lab["nm"], plain(lab["who"]), lab["conc"], host))
    os.makedirs(os.path.join(dist, "data"), exist_ok=True)
    shutil.copy(os.path.join(ROOT, "data", "essays.json"), os.path.join(dist, "data", "essays.json"))
    if links:
        shutil.copy(lp, os.path.join(dist, "data", "link-health.json"))
    key = open(os.path.join(SITE, "indexnow-key.txt")).read().strip()
    open(os.path.join(dist, key + ".txt"), "w").write(key + "\n")
    open(os.path.join(dist, "robots.txt"), "w").write("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % cfg.url)
    lastmod = max(content.get("synced") or cfg.built, (links or {}).get("checked") or "")
    open(os.path.join(dist, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n' % "\n".join(
        "<url><loc>%s</loc><lastmod>%s</lastmod></url>" % (e(cfg.url + "/" + p), lastmod) for p in pages))
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    open(os.path.join(ROOT, "build", "urls.txt"), "w").write("\n".join(cfg.url + "/" + p for p in pages) + "\n")
    return cfg, content, pages


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    cfg, content, pages = build(a.out)
    print("built %d labs, %d indexable pages, for %s" % (len(content["labs"]), len(pages), cfg.url))
