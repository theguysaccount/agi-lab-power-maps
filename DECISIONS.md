# Decisions

1. **Build on top, replace nothing.** Both essays are live; they stay the canonical home of the argument. This companion
   indexes only what is new (per-lab pages, method, sources) and keeps its archived essay copies `noindex`.
2. **Mirror, never author.** Lab facts are extracted verbatim from the live essays' own data; the tests and the live
   self-test fail if a lab page stops repeating the essays word for word.
3. **Parse data, never run it.** The essays keep their data in JavaScript arrays. A small tokenizer turns those literals into
   JSON and refuses anything that is not plain data, so no remote code runs in the build.
4. **Follow the live essays.** If the authors change the essays, the weekly sync rebuilds the lab pages from the new text
   after validation (six labs, every field, resolvable reference numbers) and opens an issue so a person can read the diff.
5. **Dates the reader can act on.** Each page shows the essays' own "as of" date, the publication month, the last sync and
   the last link check, and flags a review after six months.
6. **Disclose the source's stance.** The method page says the essays were built for Persist Ventures and advocate their
   own model (Orgoneism); the lab pages reproduce the mapping, not the proposal. Lawful whistleblower resources are linked;
   nothing asks anyone to breach an agreement.
