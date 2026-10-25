"""Compatibility entry point for the current DH013 batch-1 proposal.

The old pre-motive-rewrite numeric proposal is superseded by
finalize_dh013_batch1.py and DH013_BATCH1_161_165_FINAL_PROPOSAL.md.
"""
from pathlib import Path
import runpy
import sys

if __name__ == '__main__':
    if '--check-catalog' in sys.argv:
        sys.argv[sys.argv.index('--check-catalog')] = '--check'
    runpy.run_path(str(Path(__file__).with_name('finalize_dh013_batch1.py')), run_name='__main__')
