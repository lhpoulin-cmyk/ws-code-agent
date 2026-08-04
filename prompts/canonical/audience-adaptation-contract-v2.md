# audience-adaptation-v2

Adapt the accepted conversational baseline for the named audience. Preserve its human meaning, the original source's facts and unresolved matters, and the accepted integrity boundary. Audience profiles change presentation, not truth or authority.

Do not reply to the author, discuss this task in the output, add facts, decisions, recommendations, or certainty, remove inconvenient facts, hide risk or uncertainty, or use condescending explanation. Return exactly one audience adaptation and no commentary. The result remains REVIEW_REQUIRED.

Return exactly one JSON object with exactly these top-level fields:

* `integrity_findings`: an array of one or more objects, each containing exactly `category` and `detail`;
* `audience_adaptation`: one non-empty string.

Use only these integrity categories: `confirmed_conflict`, `apparent_conflict_requiring_authority_review`, `unsupported_claim`, `ambiguity`, and `no_material_issue_found`. Use underscore spelling exactly. `no_material_issue_found` must be exactly one concise, non-blocking finding and may not coexist with another finding. It means only that no new material integrity issue was identified in this adaptation; it does not mean the audience version is accepted.
