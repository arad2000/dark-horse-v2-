# S Incomplete-Response Policy Lock

Status: implementation contract for Draft PR on deploy/liara-commercial-sandbox.
Base commit: 57698ecb0117f0f0b503fb8a046ad0f00f2cd747.

## Decision

An S score is numeric only when all 25 Strategy questions have one valid answer each. A valid answer is a string containing exactly one of A, B, C, D, or E after trimming surrounding whitespace and case-normalization. The request must contain exactly the 25 keys sjt_1 through sjt_25. Missing keys, null/empty values, non-A–E values, extra/unknown keys, or a non-dictionary passed directly to the engine make the S assessment incomplete. At the HTTP layer, the request model requires a dictionary; a non-dictionary payload may be rejected with HTTP 422.

## Scoring

For a complete profile, the deploy formula is unchanged:

S = (1/25) × Σ from i=1 to 25 of (chosen weight for i / maximum weight in row i).

No range-normalized S formula is activated. The numerator, per-cell normalization, fixed 25-question denominator, and complete-profile output remain unchanged.

For an incomplete profile, S is null, with status incomplete_s_responses. It is not coerced to zero, averaged over answered questions, used in Total, included in ranking, selected as best branch, or persisted as a numeric recommendation.

## HTTP/API contract

Both POST /api/v2/darkhorse/discover and POST /api/v2/darkhorse/branch-discovery return HTTP 200 for a dictionary-shaped S payload that is incomplete or has extra/unknown S keys. The JSON result carries s_assessment.score: null, s_assessment.status: incomplete_s_responses, valid_answers, and expected_answers: 25. This preserves compatibility for clients that expect a successful JSON response while making non-rankability explicit.

The API model does not reject a short/long dictionary solely on a minimum/maximum item-count constraint; the engine applies the exact 25-key contract. The existing overall request-body byte cap remains in force. Non-dictionary payloads may still fail request-model validation (HTTP 422).

When S is incomplete, the API does not persist a numeric recommendation result. A session may still be created under the existing journey/session contract.

## Regression coverage

- Complete 25-answer profile: same selected-cell ratio mean, verified to 12 decimal places against the formula.
- 24 valid responses: incomplete, score null, no ranked results.
- Five strongest answers: incomplete, never 1.0 or 0.2.
- Null, invalid A–E option, and unknown key: incomplete.
- Both API discovery routes: default HTTP 200 response contract, incomplete flag carried to response, no numeric-result persistence.

## Scope locks

This change does not edit Strategy/Value weights, majors JSON, V scoring, Total thresholds, branch M scoring, the frontend journey, Hybrid/cutover, or expected scientific/membership fingerprints. No sync with main is included.
