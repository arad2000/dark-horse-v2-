# Explorer copy preview

Standalone approved Persian review fixture: one realm, five passages, fourteen paths. Preview never imports production app code, connects to an API, or stores choices. Serve this directory only for preview.

Descriptions with three example activities are displayed as lists. In production the same approved lines are stored, newline-separated, in the existing description field; the route renderer displays escaped list items for explorer only. These are examples within ONE existing selectable route, not new questions or choices. No schema/mapping change.

Tests lock fixture equality, IDs/order/mappings and every unapproved field against the 8e3a0f9 main baseline via a shallow-clone-safe fingerprint. Prior health/builder copy stays independently locked; their surrounding-data hashes include this reviewed explorer update.

Scope excludes other realm copy, global instructions, CSS/theme, main motive cards, forty questions, scoring, auth, purchase, database and deployment. No real-device or student comprehension certification. Draft only; merge requires separate approval.
