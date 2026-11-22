# 3. Compare on today's boundaries

**Status:** accepted

**Context:** When a village is absorbed on 1 January, its neighbour's numbers jump and the village disappears. Comparing raw files across the merger produces a false lead, and a coverage check that expects the old key holds a clean file.

**Decision:** The official list of boundary changes is ingested as a source. Every comparison harmonises past quarters to the boundaries of the period being judged, following chains of mergers. A withheld part makes the merged value unknown, never zero.

**Consequences:** The ablation without boundary changes held about 14 clean files a season and found a third of the stories.
