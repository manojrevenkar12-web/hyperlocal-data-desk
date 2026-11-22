# 5. Call a district only when the projection clears

**Status:** accepted

**Context:** Villages report first. Calling a district once half its municipalities have counted called about two districts a night for the wrong party on the dev world. Waiting for the last count is always right, but late.

**Decision:**
- Project unreported municipalities with the district's swing, shrunk to the Land's swing while few have reported.
- Call when the leader's margin minus 1.96 standard deviations is above zero, after at least 15% of the expected votes.
- Hold municipal reports in which a party moves more than 20 points, until corrected or for 30 minutes.

**Consequences:** No wrong calls on the dev world, a median of 20 minutes before the count ends, and fewer municipality-minutes showing a wrong result.
