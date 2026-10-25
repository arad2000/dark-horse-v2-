# Runtime environments and release evidence

## Deployment boundary

- **`main` → GitHub Pages:** the public static product under `docs/`, including `docs/index.html` and its browser assets. A successful Pages workflow verifies the frontend deployment only.
- **`deploy/liara-commercial-sandbox` → Liara API:** the FastAPI service at `https://api.asbe-siah.ir`. API runtime evidence must be read from that branch and the live API; it is not established by a successful Pages deployment.

Do not merge API-only code into `main` merely to deploy it, or assume that a Pages success changed Liara.

## Live runtime fingerprint

The deploy branch exposes `GET /__runtime_fingerprint`. The response includes the aggregate `scoring_build_fingerprint`, per-file `scoring_fingerprinted_files`, diagnostic `runtime_code_files`, catalog blob IDs, and informational fields such as `git_sha`, `runtime_commit`, and `runtime_version`.

The workflow [Liara Runtime Lock](https://github.com/arad2000/dark-horse-v2-/blob/deploy/liara-commercial-sandbox/.github/workflows/liara-runtime-lock.yml) checks out the pushed deploy commit and computes a SHA-256 aggregate plus individual SHA-256 hashes for:

- `dark_horse_engine_v2.py`
- `docs/data/micro_motives.json`
- `docs/data/questions_v2.json`
- `majors_database_v2.json`
- `trait_map_v3.json`
- `value_poles_v2.json`
- `school_branches_v2.json`

It also compares hashes for `main_v2.py` and `admission_chance_api.py` against `runtime_code_files`. The lock passes only after the aggregate and per-file scoring hashes match and both runtime-code hashes match. It retries while deployment is catching up and fails if the live fingerprint does not converge.

## Interpreting commit metadata

`runtime_commit` / `git_sha` come from environment variables (`GIT_COMMIT`, `SOURCE_COMMIT`, `COMMIT_SHA`, or `LIARA_GIT_COMMIT`). A stale value is possible and is **not** sufficient evidence that the live files match the pushed source. Use the fingerprint and per-file hash comparison as the runtime-content evidence; report commit metadata separately.

Do not manually change Liara's `GIT_COMMIT`, trigger a manual redeploy, or alter runtime settings solely to make metadata look current. Those actions require a separate explicit supervisor instruction.

## Release checklist

1. For frontend changes, verify the Pages workflow on `main`.
2. For API changes, verify the Runtime Lock result for the exact deploy push.
3. Report the checked-out commit, aggregate fingerprint result, any per-file mismatch, and `runtime_commit` as informational metadata.
4. Keep the two release paths and their evidence separate.
