# Main branch governance

## Required gate
The intended required check for protected `main` is `Purchase UI regression` until the commercial backend is reconciled into the canonical main build. After backend reconciliation, replace or supplement it with `Commercial Backend CI`.

## Protection policy
`main` should require pull requests, at least one passing required status check, and no force pushes. The current GitHub connection can read repository state but does not have administration permission to write branch-protection or ruleset settings.

## Release rule
No direct merge to `main` for Hybrid work. PR #42 remains Draft until the current main has been reconciled and the real staging gate has produced acceptance evidence.
