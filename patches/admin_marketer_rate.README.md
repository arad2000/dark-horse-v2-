# Admin sets a marketer's commission rate after creation

## Why this is needed

The live API lets an operator create a marketer with a rate but gives them no
way to change it afterwards. The console exposes only:

- `POST /api/v1/admin/marketers`
- `POST /api/v1/admin/marketers/codes`

There is no `PUT`, `PATCH` or `DELETE` for a marketer. So a rate entered later —
or a correction — had nowhere to go: the only value the system could ever keep
was whatever was passed at creation time, and a marketer created without a rate
stayed at 0 bps permanently.

That is the "the system fixes the percentage" symptom: not a hidden default, but
an immutable column with no write path.

## Scope

One `PATCH` route and one service function.

**No schema change and no migration.** The column
`referral_marketers.commission_bps` already exists, is `NOT NULL`, and already
carries `ck_commission_bps_range` (0..10000). This patch only adds a way to
write it.

## What is deliberately *not* done

- **Past money is not touched.** Each paid order keeps its own
  `commission_bps_snapshot`; a new rate applies only to orders placed after it is
  saved. Re-pricing settled history would silently rewrite what an operator owes.
- The credit ledger, orders and payments are not read or written.
- **No default rate is invented.** The operator's number is stored verbatim as
  basis points. `0` is a legitimate value meaning "no commission yet".
- Self-service marketer rows and their codes are not modified.

## Apply

```bash
git apply patches/admin_marketer_rate.patch
```

Auth is the same dependency as every other referral-admin route:
`current_referral_manager` (admin role).

## Contract

```
PATCH /api/v1/admin/marketers/{marketer_id}/commission
body: {"commission_bps": 0..10000}       # integer basis points

200: {"marketer_id", "commission_bps", "commission_percent", "updated": true}
400: value out of range, or not an integer
403: caller is not an admin
404: unknown marketer
```

`commission_percent` is returned as `bps / 100`, so `2350 -> 23.5`. This matches
what `POST /marketers` and `GET /marketers/report` already return, so the console
can use one display path.
