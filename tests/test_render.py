import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('render_pdf', Path(__file__).resolve().parents[1] / 'scripts/render_pdf.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RenderTests(unittest.TestCase):
    def test_html_to_pdf(self):
        if not (shutil.which('google-chrome') or shutil.which('chromium')):
            self.skipTest('Chrome not installed')
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / 'test.html'
            source.write_text('<!doctype html><html><body><h1>Arrakis document test</h1></body></html>')
            output = module.render(source, Path(d) / 'result.pdf')
            self.assertTrue(output.read_bytes().startswith(b'%PDF-'))
            self.assertGreater(output.stat().st_size, 1000)

    def test_reject_non_html(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / 'bad.txt'
            source.write_text('No')
            with self.assertRaises(ValueError):
                module.render(source, Path(d) / 'bad.pdf')
