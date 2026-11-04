# Record-major-map: stable and current-reference test contracts

Scope: supervisor-authorized test contract on `deploy/liara-commercial-sandbox`,
base `249ddf3b7aa38885ea90625543ad8a1c2bb355ce` (after #356).
This document is not scientific approval or authorization to edit reference data.

## 1. Stable IDs 1–160

Keep exact membership 1..160, count 160 and the existing fingerprint helpers and
expected values unchanged:
- legacy name / weights-version fingerprint: `15ce7c0ad63de857`;
- legacy full name / version / Strategy / Value fingerprint: `e0e81b6b783c1007`.

The historical total-catalog guard `len(source) == 176` belongs to neither this
stable subset nor a fingerprint definition. Remove only that global-size coupling;
never replace either digest, weaken the 160-row guard, or exclude a stable ID.

## 2. Current catalog coverage

`record_major_map.load_major_id_name_map` reads the whole official
`majors_database_v2.json`. Require all source IDs, one map entry per source row,
and the exact stripped reference name for every ID. Use the source length, not
historical rollout total 176. Current source length is 230; no data change is made.
Later IDs remain covered even though they are not part of historical wave1.

## 3. Historical wave1 is not a current capacity-stub assertion

Wave1 remains exactly IDs 161–176 with the existing explicit ID/name table.
The former claim that *every ID >=161* belongs to wave1 is invalid; narrowing
that historical cohort to its original 16 IDs is intentional, not a way to drop
current-catalog coverage (section 2 covers all IDs).

In the current official reference all 16 wave1 rows are handcrafted,
motive-driven profiles. Test those explicit current states, non-stub metadata,
seven distinct non-placeholder motive codes and nonempty archetype/version.
Keep every historical wave1 ID/name assertion. Do not relabel the other 54 later
IDs, change membership/weights, or infer a new fingerprint for these rows.

Only record-major-map tests and this document may change in this wave. Existing
fingerprint assertions, scientific/reference JSON, loader, engine and gates stay
unchanged. No env-db, capacity-unknown, canonical or 404 work is authorized.
