# Working in this repository

## Fast feedback

```bash
uv run pytest -q                       # about a minute
uv run ruff check src tests && uv run mypy
uv run desk study --world dev          # about three minutes on six processes
cd web && npm test && npm run check
```

## The invariants

1. **The truth stays in the world.** Only `src/world` and the lab's scoring know what really happened. `src/desk` never imports `world` or `lab`; a test checks the imports.
2. **The world does not read the desk's settings.** The world has its own layouts and conventions and never opens `sources.json`, `desk.json`, `designs.json`, `gates.json` or `lab.json`. It imports only the vocabulary from the desk (`desk.domain`, `desk.numbers`, `desk.election` types and `desk.notes` templates for the stand-in writer). A test checks it.
3. **Same luck for every design.** All randomness is keyed by seed and purpose (`keyed`). Every design reads the same bytes with the same model mistakes; a test checks it.
4. **Adapters refuse, they do not guess.** An unknown column, unit or number format raises `ParseError`, and the release goes to quarantine.
5. **The model writes, code checks the numbers.** No draft reaches a reporter or a reader unless every number in it matches a fact. A refused draft is replaced by the template and the reason is logged.
6. **A secret cell is never a zero.** Withheld values stay `None` through every step, and a text says they are withheld.
7. **The store never changes a decision.** Memory, DuckDB and Postgres give the same releases, statuses and leads; a test checks it.
8. **Settings in config, facts in code.** Thresholds, capacities, units, costs, seeds and gates live in `config/`. The official signs, key formats and the calendar are code.
9. **Generated reports.** `reports/*.json`, the results block of `README.md` and `web/static/data` are written by `desk study`, `desk readme` and `desk web-data`. Never edit them by hand.

## The held-out rule

Tune on the dev world only (`config/world.json`, `config/layouts.dev.json`, seeds 1–6). The held-out world (`config/heldout.json`, `config/layouts.heldout.json`, seeds 8101–8106) runs once with `desk study --world heldout`, which writes `reports/heldout.lock`. Do not play designs on held-out seeds, read held-out files or change the desk because of held-out numbers. If the desk changes after that, say so in the README and an ADR, and keep the lock.
