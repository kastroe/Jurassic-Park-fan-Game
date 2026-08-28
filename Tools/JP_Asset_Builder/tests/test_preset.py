"""Minimal offline validation for the electric-fence preset file."""

import json
from pathlib import Path
import unittest


class ElectricFencePresetTests(unittest.TestCase):
    def test_required_defaults_are_valid(self):
        preset_path = Path(__file__).resolve().parents[1] / "presets" / "electric_fence.json"
        params = json.loads(preset_path.read_text(encoding="utf-8"))
        self.assertGreater(params["section_length_m"], 0)
        self.assertGreater(params["post_height_m"], 0)
        self.assertGreaterEqual(params["wire_count"], 1)
        self.assertLessEqual(params["wire_start_height_m"], params["wire_end_height_m"])
        self.assertLessEqual(params["wire_end_height_m"], params["post_height_m"])
        self.assertTrue(params["mid_post_enabled"])
        self.assertGreater(params["mid_post_x_m"], 0)
        self.assertLess(params["mid_post_x_m"], params["section_length_m"])


if __name__ == "__main__":
    unittest.main()
