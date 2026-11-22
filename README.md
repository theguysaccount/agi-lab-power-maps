# AGI Lab Power Maps: who controls the six frontier labs

**Live:** https://theguysaccount.github.io/agi-lab-power-maps/

One page per lab (OpenAI, Anthropic, Google DeepMind, Meta, xAI, DeepSeek): who holds ultimate control, the chain of
command, the essays' editorial concentration score, the sources cited and when each fact was last verified.

Everything here comes from two visual essays that stay live where they are:
[Who Would Own God?](https://power.scalingefficiency.com/) and [The People Inside](https://fix.agireadiness.com/).
This companion **adds structure, sources, dates and link checks, and no claims of its own**:

- `scripts/sync.py` copies both live essays weekly and extracts their lab data (`LABS`, `ORGS`, `FIXES`, the numbered
  references) without executing any of their code. If the essays change, the lab pages follow after validation.
- Lab pages, the method page and the sources page are new and indexed. Archived copies of the essays are `noindex`
  with the live essays as canonical.
- Every lab page says when its facts date from ("as of late 2025 / early 2026", published May 2026) and flags a review
  once that is more than six months old.

## Run

```bash
python3 scripts/sync.py            # copy the live essays and extract data/essays.json
python3 scripts/linkcheck.py       # check every linked source the essays cite
python3 site/build.py && python3 scripts/og.py dist
python3 -m http.server 8901 --directory dist
```

## Test

```bash
python3 -m unittest discover -s tests -t .   # extraction from saved copies, validation, verbatim pages, review dates
scripts/e2e.sh                               # headless Chrome: six labs, each repeating the essays verbatim
```

Operations and keys: [OPERATIONS.md](OPERATIONS.md). Code: MIT. The essays' text belongs to their authors.
