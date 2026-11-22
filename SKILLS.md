# Repeatable tasks

## Add a source
1. Add its spec to `config/sources.json`: `id`, `indicator`, `format` (csv, json, html), accepted column names per role, expected unit, known unit conversions, decimal separator.
2. If its layout is new, add an adapter class in `src/desk/sources.py` that meets the `Adapter` contract (bytes in, `ParsedRelease` out or `ParseError`), and register it in `ADAPTERS`.
3. Add the indicator's wording to `indicators` in the same file (label and unit in German).
4. Test with a real sample file in `tests/test_sources_checks.py`, including one malformed version that must raise.
5. For the lab, give the world a matching indicator in `config/world.json` (the world keeps its own layout, never the desk's spec).

## A file was quarantined
1. `uv run desk ingest --source <id> --file <path>` prints the failed checks.
2. If the office changed its layout for good, update the spec (a new column name or unit label) and add the sample to the tests; never loosen a check to let one file through.
3. Ask the office for a corrected file; ingest it when it arrives. The quarantined release stays in the store with its reason.

## Tune the lead finder
Only on the dev world. Change `config/desk.json` (`fdr`, `min_ratio`, `min_abs`, `history_quarters`), run `uv run desk study --world dev`, and compare "stories in the top 8" and "strong leads that are stories". Record the reason in an ADR.

## Check the statistics in R
`uv run desk r-check && Rscript r/check_leads.R reports/r-check.csv` reproduces every lead probability in R; CI runs it.

## Add a design or ablation
Add an entry to `config/designs.json` (`kind` desk with `settings` overrides, or a new baseline in `src/lab/play.py`), run the study and `uv run desk readme`.

## Publish a chart
`desk.publish.datawrapper_chart(...)` builds the payload; `publish_datawrapper(payload, token)` creates, uploads and publishes it. The token comes from the environment, never from config.

## Refresh the app and screenshots
`uv run desk web-data`, then in `web/`: `npm run build && npm run shots` (system Chrome at `/usr/bin/google-chrome`, or set `CHROME`).

## Run the held-out world
Only once, when the desk is final: `uv run desk study --world heldout && uv run desk readme && uv run desk web-data`, then commit `reports/heldout.json` and `reports/heldout.lock`.
