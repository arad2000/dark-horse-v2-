from pathlib import Path
import re


def test_alembic_chain_is_linear_from_0001_to_0007():
    versions_dir = Path("alembic/versions")
    expected = [
        "0001_initial_hybrid_schema",
        "0002_auth_billing",
        "0003_credit_based_entitlements",
        "0004_txn_unique",
        "0005_payment_txn_partial_unique",
        "0006_feedback_submissions",
        "0007_auth_challenges_saved_results",
    ]

    revisions = {}
    for path in sorted(versions_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        revision_match = re.search(r'^revision\\s*=\\s*[\"\\\']([^\"\\\']+)[\"\\\']', text, re.MULTILINE)
        down_match = re.search(r'^down_revision\\s*=\\s*(None|[\"\\\']([^\"\\\']+)[\"\\\'])', text, re.MULTILINE)
        if revision_match:
            revisions[revision_match.group(1)] = None if not down_match or down_match.group(1) == "None" else down_match.group(2)

    assert list(revisions) == expected
    assert revisions[expected[0]] is None
    for current, previous in zip(expected[1:], expected[:-1]):
        assert revisions[current] == previous
