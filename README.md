# SDR Engine – Massimo Mauri

Proposal by **Massimo Mauri** for the Revenue Operations Manager (SDR / BDR) role at Perk, Barcelona.
Not affiliated with or endorsed by Perk. Every account in the demo is fictional.

- `docs/index.html` – the published page (GitHub Pages serves `/docs`): brief, playbook, live routing board, stack and AI roadmap, first 90 days.
- `docs/director/` – earlier version prepared for the Director of GTM Engineering role.
- `prototype/` – Python reference pipeline: enrichment waterfall (mocked providers), signal contracts with decay,
  ICP fit scoring, rules of engagement (Global vs regional pods), routing with capacity and cooldown guards,
  account briefs and idempotent CRM write-back payloads.
- `site/` – page templates and build scripts.

## Run

```bash
cd prototype
python3 -m pytest -q gtm/tests        # 11 tests
python3 -m gtm.pipeline --reset       # first run: creates actions
python3 -m gtm.pipeline               # re-run: 0 new actions, all duplicates skipped
python3 ../site/build_sdr.py          # rebuild site/sdr.html and docs/index.html
```
