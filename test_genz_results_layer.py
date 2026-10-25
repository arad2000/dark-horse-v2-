import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSS = ROOT / "docs" / "genz_results_layer.css"
JS = ROOT / "docs" / "genz_results_enhance.js"
INDEX = ROOT / "docs" / "index.html"


class GenZResultsLayerTests(unittest.TestCase):
    def test_presentation_assets_exist(self):
        self.assertTrue(CSS.exists())
        self.assertTrue(JS.exists())

    def test_css_is_presentation_only(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertNotIn("fetch(", css)
        self.assertNotIn("XMLHttpRequest", css)
        self.assertNotIn("localStorage", css)
        self.assertIn(".dh-result-card", css)
        self.assertIn("prefers-reduced-motion", css)

    def test_js_only_adds_visual_hooks(self):
        js = JS.read_text(encoding="utf-8")
        self.assertNotIn("fetch(", js)
        self.assertNotIn("XMLHttpRequest", js)
        self.assertNotIn("localStorage", js)
        self.assertIn("dh-result-card", js)
        self.assertIn("MutationObserver", js)

    def test_assets_load_after_existing_ui_styles(self):
        html = INDEX.read_text(encoding="utf-8")
        visual_pos = html.index('href="genz_visual_layer.css?v=1"')
        result_pos = html.index('href="genz_results_layer.css?v=1"')
        enhance_pos = html.index('src="genz_results_enhance.js?v=1"')
        self.assertLess(visual_pos, result_pos)
        self.assertLess(result_pos, enhance_pos)


if __name__ == "__main__":
    unittest.main()
