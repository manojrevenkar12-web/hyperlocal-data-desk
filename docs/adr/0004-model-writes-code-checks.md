# 4. The model writes, code checks every number

**Status:** accepted

**Context:** A model writes readable German notes but sometimes slips a decimal, changes the comparison base or flips "gestiegen" and "gesunken". A wrong number in a lead note costs a reporter hours; in an automated text it costs the paper's credibility in 1,101 places.

**Decision:** Every draft is checked by `check_numbers`. Every number must match a fact at the precision shown, and direction words must match the sign of the change. A refused draft is replaced by the template, and the reason is shown to the reporter. Automated municipal texts are templates filled from stored facts.

**Consequences:** On the dev world, no wrong number reached a note or a text. Without the check, about one note in ten carried one. The template is plainer than a model's draft, and that is accepted.
