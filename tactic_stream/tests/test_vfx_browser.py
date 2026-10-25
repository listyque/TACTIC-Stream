"""Browser execution of original VFX scripts against an owned temporary server."""

import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

from pyasm.search import Search
import test_transport as transport
import test_vfx_standard_widgets as standard


class VfxBrowser(unittest.TestCase):
    setUp = standard.VfxStandardWidgets.setUp

    def test_planner_report_review(self):
        shot = Search('vfx/shot').get_sobject()
        snapshot = self.api.dispatch(
            'create_snapshot', (self.auth, shot.get_search_key(), 'animation')
        )
        self.api.dispatch(
            'insert',
            (
                self.auth,
                'vfx/review',
                dict(
                    code='DAILY',
                    type='daily',
                    description='Team review',
                    date='2026-10-25',
                ),
            ),
        )

        class Host:
            store = self.store
            server = None
            start_server = classmethod(transport.Transport.start_server.__func__)
            stop_server = classmethod(transport.Transport.stop_server.__func__)

        from tactic_stream.server.app import create_app

        with patch(
            'test_transport.create_app',
            side_effect=lambda data_dir: create_app(data_dir, event_collector=False),
        ):
            Host.start_server()
        self.addCleanup(Host.stop_server)
        root = Path(__file__).resolve().parents[1]
        environment = dict(
            os.environ,
            VFX_URL=Host.url,
            VFX_TICKET=self.auth['ticket'],
            VFX_PROJECT=self.auth['project'],
            VFX_SHOT=shot.get_search_key(),
            VFX_SNAPSHOT=snapshot['__search_key__'],
            PLAYWRIGHT_BROWSERS_PATH=str(root / '.browser-cache'),
        )
        process = subprocess.Popen(
            [shutil.which('node'), 'tests/vfx_composition.mjs'],
            cwd=root / 'frontend',
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
        )
        try:
            output, _ = process.communicate(timeout=100)
        finally:
            if process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(
                        ['taskkill', '/PID', str(process.pid), '/T', '/F'],
                        capture_output=True,
                        check=False,
                    )
                else:
                    process.kill()
                process.wait(timeout=10)
        self.assertEqual(process.returncode, 0, output)
        search = Search('vfx/submission')
        search.add_filter('snapshot_code', snapshot['code'])
        self.assertEqual(len(search.get_sobjects()), 1)
