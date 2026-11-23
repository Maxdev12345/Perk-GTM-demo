# Perk GTM Engine – demo

Proposal by **Massimo Mauri** for the Director of GTM Engineering role at Perk. Not affiliated with Perk. All accounts are fictional.

- `docs/index.html` – the published page (GitHub Pages serves this folder).

- `prototype/` – Python reference pipeline: enrichment waterfall (mocked providers), signal contracts with decay,
  Travel/Spend fit scoring, routing with capacity and cooldown guards, account briefs, idempotent Salesforce write-back payloads.
- `site/` – interactive page. `build.py` injects the latest run into `template.html` -> `index.html`.

## Run

```bash
cd prototype
python3 -m pytest -q gtm/tests        # 10 tests
python3 -m gtm.pipeline --reset       # first run: creates actions
python3 -m gtm.pipeline               # re-run: 0 new actions, all duplicates skipped
python3 ../site/build.py              # rebuild the artifact page
python3 ../site/build_deploy.py       # rebuild the standalone page, then copy deploy/index.html to docs/
```

Optional: `GTM_BRIEF_ENGINE=claude` generates briefs with Claude (needs `pip install anthropic` and an API key).
Without it the deterministic template engine runs; any API failure falls back to the template.
