# 1. Adapters refuse instead of guessing

**Status:** accepted

**Context:** Offices change their files without notice: a unit line says "1.000", a column is inserted, a script writes English separators, last quarter's file is re-sent. A routine that takes column three and ignores the unit line prints wrong numbers for a whole Land. On the dev world the spreadsheet routine published about 4.8 broken files a season.

**Decision:** Each source has a spec (column names per role, unit labels with their factors, decimal separator). Adapters read by name and convert known units. They raise on anything unknown. Blocking checks then look at coverage, duplicates, district totals, staleness and whole counts. A failing release is quarantined and queried with the office.

**Consequences:** No broken file reached readers on the dev world, and no clean file was held. A quarantine delays a release by the office's answer (seven days in the lab). The held-out world adds layouts the dev world never used, and the README reports what happened.
