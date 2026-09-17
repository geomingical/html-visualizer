"""Regression checks for the teaching route without weakening shared checks."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify", ROOT / "skills/html-visualizer/scripts/verify.py"
)
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


class TeachingModeTests(unittest.TestCase):
    def inspect(self, mode="", script=""):
        marker = '<meta content="teaching-companion" name="html-visualizer-mode">' if mode else ""
        page = ('<!doctype html><html><head><title>課程伴讀</title>' + marker
                + '</head><body><section class="chapter" id="motivation"><h1>為什麼學</h1>'
                + '<p>這是保留來源脈絡的連續教學內文。</p>' * 2200
                + '</section><script>window.VT_SESSION = {label:"Reader"};'
                + script + '</script></body></html>')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "reader.html"
            path.write_text(page)
            verify.results.clear()
            with patch("sys.argv", ["verify.py", str(path), "--no-layout"]), contextlib.redirect_stdout(io.StringIO()):
                status = verify.main(str(path))
            return status, list(verify.results)

    def test_long_teaching_prose_is_not_forced_into_disclosures_or_figures(self):
        status, checks = self.inspect(mode="teaching")
        self.assertEqual(status, 0)
        self.assertTrue(any(mark == verify.WARN and "來源覆蓋" in label for mark, label, _ in checks))
        self.assertTrue(any("motivation" in detail for _, _, detail in checks))

    def test_existing_explainer_contract_remains(self):
        status, checks = self.inspect()
        self.assertEqual(status, 1)
        failures = {label for mark, label, _ in checks if mark == verify.BAD}
        self.assertIn("長文件有漸進揭露", failures)

    @unittest.skipUnless(verify.shutil.which("node"), "node is required to check syntax")
    def test_teaching_marker_does_not_hide_broken_javascript(self):
        status, checks = self.inspect(mode="teaching", script="const broken = ;")
        self.assertEqual(status, 1)
        self.assertTrue(any(mark == verify.BAD and "語法錯" in label for mark, label, _ in checks))

    def test_mode_is_explicit_and_independent_of_attribute_order(self):
        profile = verify.document_profile("<meta content='teaching-companion' name='html-visualizer-mode'><section class='body' id='first'></section>")
        self.assertEqual(profile.mode, "teaching-companion")
        self.assertEqual(profile.sections, ["first"])
        self.assertIsNone(verify.document_profile("<h1>教學伴讀 teaching-companion</h1>").mode)


if __name__ == "__main__":
    unittest.main()
