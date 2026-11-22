# Health route copy review

Standalone Persian copy preview approved in conversation. Serve this directory only with `python -m http.server 8080 --bind 0.0.0.0 --directory prototypes/health-copy` from the repository root. It has no API/auth/payment integration or browser persistence. Its neutral review layout is not an app theme change.

`copy.json` is the approved review fixture: 1 neighborhood, 6 passages and 23 narrow paths. It is not loaded by the production app. The approved title/description pairs are applied to `motto`/`description` in `docs/data.js`; IDs, order and major-code prefix mappings remain unchanged. The app's existing renderer and selection rules are retained. Other neighborhoods, global stage guidance, main motive cards and the forty questions are out of scope.

Validation: `node tests/test_health_route_copy.js` compares against the branch's main baseline and verifies all route objects, allowing only approved health motto/description changes. Existing catalog, motive-route, shuffle, journey persistence, purchase, home and PWA tests were also run. No real-device visual or student comprehension test has been performed. Book alignment is a design interpretation, not validation of these groupings or scoring by the book/authors.

Draft PR only; merging or deploying requires separate authorization.
