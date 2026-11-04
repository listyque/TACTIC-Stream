"""Real supplied CG ZIP, normal browser creation and native data/file operations."""
import ast
import base64
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from xmlrpc.client import Binary, ServerProxy

import test_transport

ROOT = test_transport.ROOT


class Delivery(unittest.TestCase):
    def test_cg_zip_browser_creation_relationships_and_versions(self):
        Transport = test_transport.Transport
        archive = ROOT.parent / 'cg.zip'
        if not archive.is_file():
            self.skipTest('The supplied cg.zip is required')
        Transport.setUpClass()
        self.addCleanup(Transport.tearDownClass)
        environment = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache'),
                           STREAM_CHECK_PASSWORD='private-test-password', STREAM_CHECK_PROJECT='delivery_cg')
        def browser(script, *args):
            result = subprocess.run([shutil.which('node'), 'tests/' + script, Transport.url, *args],
                cwd=ROOT / 'frontend', env=environment, capture_output=True,
                text=True, encoding='utf-8', errors='replace', timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        browser('delivery_project.mjs', str(archive))
        with ServerProxy(Transport.url + '/tactic/default/Api/', allow_none=True) as proxy:
            ticket = proxy.get_ticket('admin', 'private-test-password')
            auth = dict(ticket=ticket, project='delivery_cg', language='python')
            sample = (ROOT / 'tools/cg_sample_data.py').read_text(encoding='utf-8')
            sample += '\nreturn run(server, project_code, disable_telegram=True)\n'
            result = proxy.execute_python_script(auth, '', dict(code=sample, project_code='delivery_cg'))['info']
            self.assertEqual(sum(result['objects'].values()), 32)
            self.assertEqual((result['tasks'], result['notes'], result['relationships']), (13, 47, 45))
            key = 'cg/assets?project=delivery_cg&code=DEMO_ROBOT'
            settings = ast.literal_eval(proxy.query(auth, 'config/prod_setting', [['key', 'versionless_mode']]))
            if settings:
                proxy.update(auth, settings[0]['__search_key__'], dict(value='copy'))
            else:
                proxy.insert(auth, 'config/prod_setting', dict(key='versionless_mode', value='copy'))
            image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP4/x8AAwAB/2+Bq7YAAAAASUVORK5CYII=')
            for version in (1, 2):
                name = 'delivery-%s.png' % version
                proxy.upload_file(auth, name, Binary(image))
                proxy.simple_checkin(auth, key, 'publish', name,
                    dict(mode='uploaded', file_type='icon', create_icon=False, keep_file_name=True))
            snapshots = ast.literal_eval(proxy.query(auth, 'sthpw/snapshot', [['search_code', 'DEMO_ROBOT'], ['context', 'publish']]))
            self.assertEqual(sorted(row['version'] for row in snapshots), [-1, 1, 2])
        browser('result_views.mjs')
