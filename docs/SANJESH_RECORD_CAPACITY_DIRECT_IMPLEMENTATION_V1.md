# Sanjesh Record Capacity Direct Path — Implementation Note v1

The direct capacity path is explicitly selected with:

```json
{
  "admission_path": "record",
  "source": "capacity",
  "periods": ["روزانه"]
}
```

## Source separation

- `source=program` keeps the existing record path based on `program2s.json`.
- `source=capacity` uses only `docs/data/sanjesh_record_capacity_full.json` plus `majors_database_v2.json` for `major_id -> major_name`.
- `source` defaults to `program`, so existing callers retain the previous behavior.
- `periods` is required when `source=capacity`; it is not a synonym table and does not implement period fallback.
- Unknown periods produce an empty result with an explicit note rather than falling back to another period.

## Hard locks

The direct path does not:
- write `sanjesh_code` or `capacity` to `program2s`;
- use `university.name`, `university_id`, or program matching;
- perform fuzzy major/university matching;
- invent an Azad period;
- change existing program-side G1–G4 / Section 2 behavior;
- calculate admission probabilities or calibration values.

## Response provenance

Each item copies `sanjesh_code`, `major_name`, `campus`, `province`, `period`, and `capacity` from the selected capacity row. The optional `quota_shares_mvp` object is passed through only when present in that row.

