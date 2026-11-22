# Builder neighborhood copy review

Standalone Persian preview: 1 neighborhood, 7 passages, 28 narrow paths. Serve only this directory for review. No API, auth, payment, scoring or browser persistence. Review layout is not an app theme change.

copy.json records the text reviewed and approved in conversation, including varied question openings. Production uses only motto/description replacements in docs/data.js; it does not import this preview. IDs, order, mappings, main motive cards and forty questions are unchanged. Global stage instructions and other neighborhoods are out of scope.

Validation: tests/test_builder_route_copy.js checks exact text against the fixture and fingerprints all remaining route data against the main baseline c11cdf9. This works with shallow CI checkouts. Health copy remains independently checked against its approved fixture. Its surrounding-data fingerprint is updated to include approved builder text. No claim of student comprehension validation or real-device visual testing; book alignment is interpretive, not author/scientific certification.

Draft PR only; no merge or manual deployment without separate authorization.
