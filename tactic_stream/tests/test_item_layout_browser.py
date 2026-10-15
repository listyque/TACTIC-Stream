"""Exercise the public editor on a private native fixture, always stopping its server."""
import os
import shutil
import subprocess
import unittest
from pathlib import Path


class ItemLayoutBrowser(unittest.TestCase):
    def test_editor_and_runtime(self):
        from test_transport import Transport
        class FixtureServer(Transport):
            pass
        FixtureServer.setUpClass()
        self.addCleanup(FixtureServer.tearDownClass)
        from tactic_stream.server.api import Api
        api = Api(FixtureServer.store)
        token = api.get_ticket('admin', 'private-test-password')
        for view in ('quick_filters@cg/assets@th_assets', 'quick_filters@plain'):
            api.dispatch('insert', (dict(ticket=token, project='admin'), 'config/widget_config',
                dict(search_type='sthpw/project', view=view, category='quick_filters',
                     config='<config><view name="%s"><values type="json">{}</values></view></config>' % view)))
        root = Path(__file__).resolve().parents[1]
        output = root / '.screenshots/item-layouts'
        output.mkdir(parents=True, exist_ok=True)
        log = output / 'browser.log'
        with log.open('w', encoding='utf-8') as stream:
            process = subprocess.Popen([shutil.which('node'), 'tests/item_layouts.mjs', FixtureServer.url, str(output)],
                cwd=root / 'frontend', env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(root / '.browser-cache')),
                stdout=stream, stderr=subprocess.STDOUT)
            try:
                process.wait(timeout=120)
            finally:
                if process.poll() is None:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, check=False)
                    else:
                        process.terminate()
                    process.wait(timeout=10)
        self.assertEqual(process.returncode, 0, log.read_text(encoding='utf-8'))
