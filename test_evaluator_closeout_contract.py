from pathlib import Path
import unittest


class EvaluatorCloseoutContractTests(unittest.TestCase):
    def test_migration_rehearsal_is_staging_only(self):
        source = Path("scripts/migration_rehearsal.py").read_text(encoding="utf-8")
        self.assertIn("--confirm-staging", source)
        self.assertIn("PROD_MARKERS", source)
        self.assertIn("POSTGRES_RUNTIME_CUTOVER_APPROVED", source)
        self.assertIn('"alembic", "downgrade", "-1"', source)
        self.assertIn('"alembic", "upgrade", "head"', source)

    def test_backup_restore_is_staging_only_and_requires_separate_restore_target(self):
        source = Path("scripts/backup_restore_rehearsal.py").read_text(encoding="utf-8")
        self.assertIn("--confirm-staging", source)
        self.assertIn("PROD_MARKERS", source)
        self.assertIn("RESTORE_DATABASE_URL", source)
        self.assertIn('"pg_dump",', source)
        self.assertIn('"--format=custom"', source)
        self.assertIn('"pg_restore",', source)
        self.assertIn('"--clean", "--if-exists"', source)
        self.assertIn("libpq_url", source)

    def test_hybrid_gate_remains_hard_false(self):
        source = Path("migration_control.py").read_text(encoding="utf-8")
        self.assertIn("POSTGRES_RUNTIME_CUTOVER_APPROVED = False", source)
        self.assertNotIn("os.getenv", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
