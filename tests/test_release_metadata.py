import unittest
from pathlib import Path

from scripts.validate_release import validate_release_metadata


class ReleaseMetadataTest(unittest.TestCase):
    def test_current_release_metadata_is_consistent(self):
        metadata = validate_release_metadata(Path(__file__).parents[1], "v1.2.2")
        self.assertEqual(metadata["version"], "1.2.2")

    def test_rejects_wrong_tag(self):
        with self.assertRaisesRegex(ValueError, "必须匹配"):
            validate_release_metadata(Path(__file__).parents[1], "v1.2.1")


if __name__ == "__main__":
    unittest.main()
