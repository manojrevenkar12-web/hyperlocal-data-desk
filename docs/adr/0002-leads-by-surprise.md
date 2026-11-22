# 2. Leads by surprise against the municipality's own history, with the false discovery rate controlled

**Status:** accepted

**Context:** Ranking by percentage change sends reporters to villages with one permit more. A plain Poisson test calls almost everything significant, because permits and business registrations come in lumps. With 1,101 tests per release, a fixed p-value cut-off lets through about one noise lead per release.

**Decision:**
- Each municipality's expectation comes from its own history, shrunk towards its district (gamma-Poisson).
- It moves with its district's change this quarter, computed without the municipality itself (after a test showed one big town moving its neighbours).
- The test is a negative binomial, with the extra wobble pooled over all municipalities.
- Strong leads are those that pass Benjamini–Hochberg at the configured rate. The rest of the capacity of eight is a marked watch list.

The rate (0.05) was chosen on the dev seeds.

**Consequences:** On the dev world, the top eight held 1.7 times as many real stories as the better baseline. About half of the strong leads were real, against 2% for the spreadsheet. The test is reproduced in R in CI.
