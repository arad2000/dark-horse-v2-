# Reviewer B — Motive tiers, Strategy/Value weights and reproducibility (F4)

**Status: OPEN — no signature is claimed.**

Method sources: F2 evidence SHA `84cd88877a620c7f717e9d98f82ed43e81e0c4cd`; F1 value-cue rubric SHA `08785995aab29214e2520c454f04a1beccbfe2f0`; `trait_map_v3.json` SHA `466280fe517b7e6ba68e54dbe8535de7444c7f4a`; value poles SHA `251d435d57b90e325ff671a4f8c69c530de61494`.

- [ ] Verify the seven Motive tier weights `[1, 1, 0.9, 0.9, 1, 0.9, 0.7]` are recorded per code, with task/source traceability and no unsupported “empirical” label.
- [ ] Confirm the S01–S25 questions and five trait labels are unchanged from the versioned question/template data.
- [ ] Recompute weighted trait prevalence per option, normalize all 25 rows, and verify every row sums to 1 within 0.002.
- [ ] Recompute `evidence_confidence`; for each option verify ≥2 code-level refs (S=trait support; C=contrast-only when needed).
- [ ] Confirm every low-confidence Strategy option (<0.70) uses the mean same-option weight from the three documented neighbors and the formula `confidence×raw + (1−confidence)×neighbor mean`.
- [ ] Recompute all 30 Value poles using `F1_value_cue_rubric.json`: direct text cue=1, mapped-trait overlap=0.5, no match=0; `0.25 + 0.70×weighted mean`; apply per-pole confidence caps and three-neighbor adjustment when confidence<0.70.
- [ ] Verify every Value pole has ≥2 code refs, every stored raw/candidate weight matches the evidence, and all candidate values match `majors_database_v2.json`.
- [ ] Confirm no engine, engine formula, Hybrid, Total, cutoff or unrelated major record changes were introduced.
- [ ] Do not sign off on numeric/psychometric validity; the rubric output is reproducible candidate evidence, not empirical calibration.

Reviewer / date / commit SHA: ____________________
