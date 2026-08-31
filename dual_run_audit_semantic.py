"""Semantic dual-run comparator for staged Hybrid validation.

JSON remains the live source of truth. PostgreSQL is staging-only.
The comparator ignores only physical branch metadata affected by deferred BIOTM
association rows and keeps algorithmic outputs strict.
"""

from dual_run_audit import main

if __name__ == "__main__":
    main()
