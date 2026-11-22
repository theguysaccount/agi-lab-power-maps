# Operations

Live at https://theguysaccount.github.io/agi-lab-power-maps/, a companion to the live essays at
https://power.scalingefficiency.com/ and https://fix.agireadiness.com/ (which this repo never touches).

## Automated jobs

| Workflow | When | What it does | How it fails safe |
|---|---|---|---|
| `weekly.yml` | Mondays 06:29 UTC, or by hand | `sync.py` copies both live essays and extracts their lab data; `linkcheck.py` checks every linked source. Commits `data/` and `archive/`, dispatches the deploy, opens or closes `ops-alert` issues. Keep-alive afterwards. | If an essay can't be fetched or no longer parses into six complete labs, nothing is written and the last good copy stays live; the run ends red with an issue. Link failures are reported only on a second failing week. |
| `deploy.yml` | Pushes that change `data/`, `archive/`, `site/` or `scripts/`; dispatched by `weekly.yml` | Tests, build, share cards, headless-Chrome check (every lab page repeats the essays verbatim), Pages deploy (retried once), the same check live, IndexNow. | Anything failing before the deploy leaves the last good deploy live. |
| `selftest.yml` | Thursdays 07:17 UTC, or by hand | `health.py`: pages answer, lab pages still match the essays' data, archives `noindex` with the live essays as canonical, sitemap correct, link check fresh (dispatches `weekly.yml` if not). Then the live end-to-end run and keep-alive. | Read-only. |
| `ci.yml` | Every push and pull request | Tests on Python 3.9 and 3.12. | — |

**Keep-alive:** `scripts/keepalive.sh` after every scheduled job. **Late schedules:** every job is safe to re-run; the
self-test dispatches the weekly job when it is stale.

## What to watch

| Signal | Where | Healthy |
|---|---|---|
| Runs | Actions tab; failure emails to the account owner | Weekly checks and self-test green |
| `essay-changed` issue | Issues tab | Read the diff of `data/essays.json`, confirm new claims are sourced, close it |
| `source-links` issue | Issues tab | None open |
| "Review due" on every lab page | Lab pages | Shown until the essays' authors update their facts and date |

## Scheduled Claude routine (recommended, set up once by a person)

The facts age; the companion must not update them itself. Quarterly, for the essays' owner (not in this repo):

> Check each lab's governance against current primary sources (company structure pages, filings, board announcements) and
> list what changed since the essays' "as of" date, with links. Propose edits to the live essays and the numbered sources;
> do not edit this companion. When the essays are updated, this repo's weekly sync picks the change up.

## Keys Jack can turn later

| Key | Why | Exact steps |
|---|---|---|
| **Custom domain** | Put the lab pages on the essays' domain | 1) SiteGround → agireadiness.com → DNS Zone Editor: `CNAME labs → theguysaccount.github.io` 2) `~/.local/bin/gh api -X PUT repos/theguysaccount/agi-lab-power-maps/pages -f cname=labs.agireadiness.com` 3) `~/.local/bin/gh variable set SITE_URL -R theguysaccount/agi-lab-power-maps -b https://labs.agireadiness.com` 4) `~/.local/bin/gh workflow run deploy.yml -R theguysaccount/agi-lab-power-maps` 5) after the certificate is issued: `~/.local/bin/gh api -X PUT repos/theguysaccount/agi-lab-power-maps/pages -F https_enforced=true`. The fix. and www records are untouched. |
| **Refresh the facts** | Clear "review due" | Update the live essays (facts, "as of" sentence, the "Built for … · <Month Year>" line). The next weekly sync follows. |
| **Specific sources** | 12 citations name only an outlet | Replace each with the article's URL in the essays' reference list. |
| **Money** | Donation or grant link | `gh variable set SUPPORT_URL -b <url>` (and `SUPPORT_LABEL`), run `deploy.yml`. |
| **Analytics** | Count source clicks and essay referrals | GoatCounter site, `gh variable set GOATCOUNTER_URL -b https://<code>.goatcounter.com/count`, run `deploy.yml`. |
| **Review window** | Change when "review due" appears | `gh variable set REVIEW_AGE_DAYS -b 120` (default 180), run `deploy.yml`. |
