# 7. What the held-out world showed

**Status:** accepted

**Context:** The held-out world ran once (`reports/heldout.json`). It had other municipalities, mergers a year later, lumpier counts (building permits with more spread), more stories and drift, and file layouts the dev world never used: swapped columns, comma-separated files and new unit labels.

**What held:**
- No wrong number reached a municipal text or a lead note.
- No broken file reached readers, and no clean file was held. The new layouts were either read correctly by name or quarantined.
- The desk's top eight per release held 1.65 times as many real stories as the better baseline, and a story cost about a fifth of a model-alone's reporter hours.
- On election night the desk called one district wrong in six nights. Calling at half counted got 8.7 wrong per night.

**What did not:** 37% of the strong leads were real stories, against a gate of 50% set on dev, where the figure was 55%. The held-out counts are lumpier. The pooled extra wobble is estimated from six quarters of history, which in this world is too short to capture spikes that come back. So more noise passes the false-discovery cut-off as strong.

**Decision:** The desk is not re-tuned on these numbers, and the held-out report stays as it ran. The next version would estimate the extra wobble per indicator from a longer history. It would treat the strong/watch split as the reporters' choice: a desk with more capacity reads further down the watch list. That version would be judged on a new held-out world.

**Consequences:** The README shows the held-out results first, including the failed gate. The ranking (top eight) carried over to unseen data; the calibration of "strong" did not.
