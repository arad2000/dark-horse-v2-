# Admission Chance — Phase 2 Senjesh-aligned contract

## Scope

This phase changes only the admission-chance module and its regression tests.
It does **not** change Dark Horse scoring/ranking, scientific JSON, Hybrid,
PostgreSQL runtime cutover, or `app.js` / `shell.js`.

## Request contract

`POST /api/v1/admission/chance`

### Canonical fields

- `major_ids`: list of discovered major IDs.
- `rank_in_quota`: **رتبه در سهمیه (کارنامه ملاک عمل انتخاب رشته سنجش)**.
- `quota_type`: one of:
  - `region_1`
  - `region_2`
  - `region_3`
  - `isargaran_25`
  - `isargaran_5`
  - `shahid`
- `province`: one of the 31 canonical Iranian province names.
- `gpa_written`: final written diploma GPA; used for academic-record admission.
- `gpa_total`: optional.
- `national_rank`: optional and never used as the academic-record rank cutoff.
- `course_types`: optional program filter.
- `diploma_type`: optional program filter.

### Backward compatibility

The previous `rank`, `region_zone`, `quota`, and `gpa` fields remain accepted.

For the legacy payload:

- `quota=azad` + `region_zone=1/2/3` resolves to `region_1/2/3`.
- Known legacy special quotas resolve to their own cutoff dimensions.
- An unknown quota never silently falls back to a zone.

## Cutoff dimensions

| quota_type | cutoff dimension |
|---|---|
| region_1 | zone_1 |
| region_2 | zone_2 |
| region_3 | zone_3 |
| isargaran_25 | isargaran_25 |
| isargaran_5 | isargaran_5 |
| shahid | shahid |

The API returns both `cutoff_dimension` and `cutoff_used` in each exam-based item.

Historical fallback is allowed only within the **same** cutoff dimension.
There is no region/quota cross-fallback.

## Bomi handling

If:

- `admission_info.bomi_type == ostani`,
- the applicant province equals the university province, and
- `cutoffs_bomi` exists,

the matching bomi cutoff is preferred.

For `ghotbi`, no province-to-pole mapping is invented; the existing
conservative warning remains:

> بومی قطبی: اعمال دقیق قطب نیازمند داده رسمی است

## Academic-record handling

For `سوابق تحصیلی` programs:

- only `gpa_written` is compared with `cutoffs_savabegh.minimum_gpa`;
- rank, quota rank, and national rank do not determine the academic label;
- when the required minimum GPA is missing, the API reports that the source
  data is incomplete rather than fabricating a rank cutoff.

## Province enum

The accepted province set is exactly:

آذربایجان شرقی، آذربایجان غربی، اردبیل، اصفهان، البرز، ایلام، بوشهر،
تهران، چهارمحال و بختیاری، خراسان جنوبی، خراسان رضوی، خراسان شمالی،
خوزستان، زنجان، سمنان، سیستان و بلوچستان، فارس، قزوین، قم، کردستان،
کرمان، کرمانشاه، کهگیلویه و بویراحمد، گلستان، گیلان، لرستان، مازندران،
مرکزی، هرمزگان، همدان، یزد.

## Safety/product boundary

The API returns qualitative labels only. It never returns a deterministic
admission percentage and retains the official-results disclaimer.
