#!/usr/bin/env python3
"""Render a local HTML document to a PDF with headless Chromium."""
import argparse
import shutil
import subprocess
from pathlib import Path


def render(source: Path, output: Path, browser=None):
    source = source.resolve(strict=True)
    if source.suffix.lower() not in ('.html', '.htm'):
        raise ValueError('Source must be an HTML document')
    browser = browser or shutil.which('chromium') or shutil.which('google-chrome')
    if not browser:
        raise RuntimeError('Chromium or Google Chrome is required')
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([
        browser, '--headless', '--disable-gpu', '--no-first-run',
        '--no-default-browser-check', '--disable-dev-shm-usage',
        '--virtual-time-budget=3000', '--print-to-pdf=' + str(output),
        source.as_uri(),
    ], capture_output=True, text=True, timeout=60)
    if proc.returncode or not output.exists() or output.stat().st_size < 1000:
        raise RuntimeError('PDF render failed: ' + proc.stderr[-1200:])
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    print(render(args.source, args.output))
