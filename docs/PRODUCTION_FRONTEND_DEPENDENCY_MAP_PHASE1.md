# Production frontend dependency map — Phase 1 quota consolidation

> مبنا: entrypoint تولیدی docs/index.html در شاخه main مخزن. این نقشه ساختار بارگذاری production را ثبت می‌کند؛ صحت اجرای HTTP زنده از محیط ابزار مستقل تأیید نشده است.

## Load order

data.js → app.js?v=67 → feedback_bridge.js?v=2 → ux_v2_patch.js → quotes_darkhorse.js → auth_api_client.js?v=10 → quota_state_reconciler.js?v=4 → shell_runtime_fix.js?v=1 → shell.js?v=75 → quota_runtime.js?v=1 → profile_ux_v1.js?v=7 → admin_feedback_ui_v1.js?v=1 → commercial_ui.js?v=32 → external_links_fix_v1.js?v=2 → purchase_ui_fix.js?v=1 → password_reset_ui.js?v=1 → spark_game.js → parents.js → stories.js → poems.js → payment_return_reconcile.js?v=1 → post_auth_flow_policy.js?v=3 → pwa-boot.js?v=63 → genz_results_enhance.js?v=1

## Quota/session dependency graph

```text
auth_api_client
      │
      ├── DHAuth.quota()
      ├── DHAuth.consumeTest() ──────┐
      └── DHAuth.createPayment()    │
                                     ▼
shell.js ── DHShell.startJourney ── quota_runtime
app.js ─── displayResults / discovery ────┬───────────────┐
                                         │               │
                                         ▼               ▼
                              session UUID boot     server-authoritative
                              + fetch wrappers      consume-test
                                         │               │
                                         ├──── failure UI
                                         └──── consume adapter

quota_state_reconciler.js ── sibling; intentionally NOT merged
payment_return_reconcile.js ─ sibling; intentionally NOT merged
commercial_ui.js / purchase_ui_fix.js ─ payment/auth layers; intentionally NOT merged
```

## Phase 1 consolidation

Merged into docs/quota_runtime.js without changing public behavior:

| Previous script | Role retained in quota_runtime |
|---|---|
| journey_session_boot.js | persist/ensure journey UUID after journey start |
| quota_enforcement_bridge.js | server-authoritative discovery session + result-triggered consume + quota sync |
| quota_charge_failure_ui.js | user-visible consume failure/retry UI |
| quota_consume_session_adapter.js | preserve session UUID on legacy consume requests |

Load-order guarantee: the four blocks are kept in their historical order inside the single file, so wrapper composition remains deterministic.

## Explicitly out of scope

app.js, shell.js, commercial_ui.js, payment flow, scoring/ranking logic, Hybrid PR #42, and the sibling quota/payment reconciliation modules are not merged or rewritten in Phase 1.
