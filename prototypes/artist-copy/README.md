# Artist copy review preview

Standalone Persian review fixture: one realm, six passages, sixteen paths. IDs, order and majorCodes copied from production data without regrouping. Titles and activity examples reflect the chat-reviewed wording and final approved realm question.

Serve this directory only. The preview fetches only local copy.json, uses textContent for copy, and has no API, auth, selection persistence or scoring. Buttons navigate between review pages, not real choices. Production app does not import this preview.

The preview is standalone. Authorized production preparation is described below. No mapping, motive card, strategy/value question, engine, theme, account, purchase or database changes. No real-device or student comprehension testing claimed. Merge requires separate authorization.

## Production preparation

Authorized production preparation mirrors 23 motto/description pairs (1+6+16). Three path activities are newline-separated in the existing description field. Escaped lists remain within one route choice. Global instructions and selection behavior are unchanged.

`tests/test_artist_route_copy.js` locks exact approved copy, fixture IDs/order/mappings and all unapproved route fields using a shallow-clone-safe fingerprint of main 840b91394c326959f6a0abcc070edbf108c460af. Previous realm fixtures remain locked; only their surrounding-data fingerprints and shared cache key expectations are refreshed. All standalone JS tests passed locally. No real-device/student comprehension certification or manual deployment. Draft PR; merge requires separate approval.
