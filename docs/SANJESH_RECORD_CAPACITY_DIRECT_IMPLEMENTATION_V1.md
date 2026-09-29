# Sanjesh Record Capacity Direct Path — Implementation Note v1

The direct capacity path is explicitly selected with:

```json
{
  "admission_path": "record",
  "source": "capacity",
  "periods": ["روزانه"]
}
```

- `source=program` keeps the existing record path based on `program2s.json`.
- `source=capacity` uses only `docs/data/sanjesh_record_capacity_full.json` plus `majors_database_v2.json` for `major_id -> major_name`.
- `source` defaults to `program`, preserving existing callers.
- `periods` is required for `source=capacity`; unknown values return no rows rather than falling back to another period.
- No fuzzy matching, period fallback, Azad-period invention, program2s enrichment, scoring, Hybrid, cutover, or program-side G1–G4/Section2 changes are part of this path.

Response fields are copied from the selected capacity row: `sanjesh_code`, `major_name`, `campus`, `province`, `period`, and `capacity` as `capacity_total`. `quota_shares_mvp` is passed through only when present.
