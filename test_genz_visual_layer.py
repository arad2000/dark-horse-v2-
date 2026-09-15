import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CSS = ROOT / "docs" / "genz_visual_layer.css"
INDEX = ROOT / "docs" / "index.html"


class GenZVisualLayerTests(unittest.TestCase):
    def test_visual_layer_exists_and_is_visual_only(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn("--dh-youth", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn(".swipe-card", css)
        self.assertNotIn("fetch(", css)
        self.assertNotIn("XMLHttpRequest", css)
        self.assertNotIn("localStorage", css)

    def test_visual_layer_loaded_after_shell(self):
        html = INDEX.read_text(encoding="utf-8")
        shell_pos = html.index('href="shell.css?v=59"')
        layer_pos = html.index('href="genz_visual_layer.css?v=1"')
        self.assertLess(shell_pos, layer_pos)

    def test_gold_remains_primary_action_color(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".btn-primary:hover", css)
        self.assertIn("rgba(240, 192, 64", css)
        self.assertIn("--dh-youth: #9b8cff", css)


if __name__ == "__main__":
    unittest.main()
