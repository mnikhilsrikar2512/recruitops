import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.bootstrap_manifest import BOOTSTRAP_SCRIPTS, select_bootstrap_scripts


class BootstrapManifestTests(unittest.TestCase):
    def test_core_bootstrap_excludes_sample_data_by_default(self) -> None:
        scripts = select_bootstrap_scripts(include_sample_data=False)
        self.assertTrue(all(script.script_type != "seed-sample" for script in scripts))
        self.assertEqual(len(scripts), len(BOOTSTRAP_SCRIPTS) - 1)

    def test_bootstrap_can_include_sample_data(self) -> None:
        scripts = select_bootstrap_scripts(include_sample_data=True)
        self.assertEqual(len(scripts), len(BOOTSTRAP_SCRIPTS))
        self.assertEqual(scripts[-1].key, "004_seed_sample_business_data")


if __name__ == "__main__":
    unittest.main()
