import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.sql_runner import compute_sql_checksum, should_execute_script, split_sql_batches


class SqlRunnerTests(unittest.TestCase):
    def test_split_sql_batches_splits_on_go(self) -> None:
        batches = split_sql_batches("SELECT 1;\nGO\nSELECT 2;\nGO\n")
        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[0].sql_text, "SELECT 1;")
        self.assertEqual(batches[1].sql_text, "SELECT 2;")

    def test_split_sql_batches_honors_repeat_counts(self) -> None:
        batches = split_sql_batches("INSERT INTO demo VALUES (1);\nGO 3\n")
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0].repeat_count, 3)

    def test_compute_sql_checksum_is_stable(self) -> None:
        sql_text = "SELECT 1;\nGO\nSELECT 2;"
        self.assertEqual(compute_sql_checksum(sql_text), compute_sql_checksum(sql_text))

    def test_should_execute_script_skips_unchanged_checksum(self) -> None:
        self.assertFalse(should_execute_script("abc123", "abc123"))
        self.assertTrue(should_execute_script("abc123", "different"))
        self.assertTrue(should_execute_script("abc123", "abc123", force=True))


if __name__ == "__main__":
    unittest.main()
