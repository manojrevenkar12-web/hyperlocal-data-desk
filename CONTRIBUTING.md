# Contributing

One change per pull request, with the test that shows it. CI must be green: Python tests with Postgres/PostGIS, lint and types, the dev report reproducing byte for byte, the README block matching the reports, the R reproduction, the held-out lock, and the web app's tests, type check and build.

## Review checklist

- [ ] **Can a number reach a reader without a check?** New text or chart code must go through `check_numbers` or show only stored facts.
- [ ] **Does an adapter guess?** A new format must refuse what it does not understand; a test with a malformed file shows it.
- [ ] **Is a secret cell still a secret?** Follow `None` from the adapter to the text and the map.
- [ ] **Are boundaries handled?** Anything that compares quarters goes through `harmonise`.
- [ ] **Is a new number a setting?** Then it belongs in `config/`.
- [ ] **Did the dev report change?** Regenerate `reports/dev.json`, the README block and `web/static/data` in the same commit, and say why the numbers moved.
- [ ] **Was the held-out world touched?** It should not have been.
- [ ] **Frontend:** loading, error and empty states; nothing said by colour alone; keyboard focus visible; reduced motion respected; German copy a reporter would write.

## Reviewing a newcomer's change

Ask for the failure case first: "What does this do with a file that has an extra column? With a secret cell?" Point to the ADR behind a rule rather than restating it. Pair on the first change to the lead finder.
