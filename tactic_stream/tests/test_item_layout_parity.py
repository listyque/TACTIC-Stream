"""Compare the original item and its XML composition on identical fixture data."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

from PIL import Image, ImageChops
from pyasm.search.search import RequestContext, request_context
from pyasm.widget import WidgetConfig, WidgetConfigView
from tactic_stream.server.interface import describe_view
from tactic_stream.server.item_layout import describe_item_layout, layout_templates


class ItemLayoutParity(unittest.TestCase):
    def test_original_and_custom_items(self):
        root = Path(__file__).resolve().parents[1]
        output = root / '.screenshots/item-layout-parity'
        output.mkdir(parents=True, exist_ok=True)
        with request_context(RequestContext(None, 'admin', 'admin')):
            source = layout_templates()[0]['xml']
            config = WidgetConfig.get(view='continuous_example', xml=source, use_cache=False)
            layout = describe_item_layout(describe_view(WidgetConfigView('sthpw/note', 'continuous_example', [config])))
        (output / 'layout.json').write_text(json.dumps(layout), encoding='utf-8')
        log = output / 'browser.log'
        with log.open('w', encoding='utf-8') as stream:
            process = subprocess.Popen([shutil.which('node'), 'tests/item_layout_parity.mjs', str(output)],
                cwd=root / 'frontend', env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(root / '.browser-cache')),
                stdout=stream, stderr=subprocess.STDOUT)
            try:
                process.wait(timeout=150)
            finally:
                if process.poll() is None:
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
                    process.wait(timeout=10)
        self.assertEqual(process.returncode, 0, log.read_text(encoding='utf-8'))
        differences = []
        for row in json.loads((output / 'measurements.json').read_text(encoding='utf-8')):
            name = '%s-%s-%s' % (row['width'], row['node'], row['state'])
            with Image.open(output / (name + '-original.png')) as original, Image.open(output / (name + '-custom.png')) as custom:
                if original.size != custom.size:
                    differences.append((name, 'size', original.size, custom.size))
                # Chromium can round antialiased border channels by one on first paint.
                elif any(high > 1 for low, high in ImageChops.difference(original.convert('RGB'), custom.convert('RGB')).getextrema()):
                    differences.append((name, 'pixels', row['original'], row['custom']))
        self.assertEqual(differences, [], json.dumps(differences, indent=2))
