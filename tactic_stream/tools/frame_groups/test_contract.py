"""Shipped Handler procedures against real isolated Stream data."""
import ast
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.common import Config
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security import Login
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.security_groups import security_groups_request


class FrameGroupsBackend(unittest.TestCase):
    def test_comparison_never_copies_and_copy_direction_is_explicit(self):
        from tools import sync_tactic_frame as copies
        with tempfile.TemporaryDirectory(prefix='frame-copies-') as directory:
            root = Path(directory)
            stream = root / 'stream'
            handler = root / 'handler'
            native = handler / 'thlib/ui/qml/tactic_frame'
            stream.mkdir()
            native.mkdir(parents=True)
            (stream / 'frame.mjs').write_text('stream', encoding='utf-8')
            (native / 'frame.mjs').write_text('handler', encoding='utf-8')
            with patch.object(copies, 'SOURCE', stream):
                with self.assertRaisesRegex(AssertionError, 'copies differ'):
                    copies.sync(handler)
                self.assertEqual((native / 'frame.mjs').read_text(), 'handler')
                copies.sync(handler, copy_from='stream')
                self.assertEqual((native / 'frame.mjs').read_text(), 'stream')
                (native / 'frame.mjs').write_text('edited in handler', encoding='utf-8')
                with self.assertRaisesRegex(AssertionError, 'copies differ'):
                    copies.sync(handler)
                self.assertEqual((stream / 'frame.mjs').read_text(), 'stream')
                copies.sync(handler, copy_from='handler')
                self.assertEqual((stream / 'frame.mjs').read_text(), 'edited in handler')

    def test_shipped_handler_modules_match_stream_copy(self):
        from tools.sync_tactic_frame import sync
        sync('D:/code/th_codex', check=True)

    def test_handler_and_browser_share_revisions_and_memberships(self):
        source = Path('D:/code/th_codex/thlib/ui/security_store.py').read_text(encoding='utf-8')
        procedures = '\n\n'.join(ast.get_source_segment(source, node) for node in ast.parse(source).body if isinstance(node, ast.FunctionDef))
        with tempfile.TemporaryDirectory(prefix='frame-groups-') as directory, patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
            Config.reload_config()
            store = Store(Path(directory) / 'data')
            store.initialize(hash_password('isolated-frame-password'))
            api = Api(store)
            auth = dict(ticket=api.get_ticket('admin', 'isolated-frame-password'), project='sthpw')

            def native(expression):
                result = api.dispatch('execute_python_script', (auth, '', {'code': procedures + '\nreturn ' + expression}))
                return json.loads(result['info'])

            for name in ('alice', 'bob'):
                api.dispatch('insert', (auth, 'sthpw/login', {'login': name, 'password': hash_password('isolated-user-password')}))
            created = native("save_security_group('', 'frame_team', 'Shared group', ['alice'], [], '')")
            group = next(row for row in native('query_security_groups()')['groups'] if row['code'] == created['code'])
            with request_context(RequestContext(store, login='admin', project='sthpw')):
                api.auth.bind_security('admin', auth['ticket'])
                browser_group = next(row for row in security_groups_request('read', {})['groups'] if row['code'] == group['code'])
                self.assertEqual(group['revision'], browser_group['revision'])
                Login.get_by_login('bob').add_to_group('frame_team')
            native(f"save_security_group({group['code']!r}, 'frame_team', 'Native edit', [], ['alice'], {group['revision']!r})")
            fresh = native('query_security_groups()')
            self.assertEqual({row['login'] for row in fresh['memberships'] if row['login_group'] == 'frame_team'}, {'bob'})
            with self.assertRaisesRegex(ValueError, 'changed'):
                native(f"save_security_group({group['code']!r}, 'frame_team', 'Stale edit', [], [], {group['revision']!r})")
            revision = next(row['revision'] for row in fresh['groups'] if row['code'] == group['code'])
            with patch.object(Login, 'add_to_group', side_effect=ValueError('late native membership failure')):
                with self.assertRaisesRegex(ValueError, 'late native'):
                    native(f"save_security_group({group['code']!r}, 'frame_team', 'Must roll back', ['alice'], [], {revision!r})")
            observed = next(row for row in native('query_security_groups()')['groups'] if row['code'] == group['code'])
            self.assertEqual(observed['description'], 'Native edit')
            self.assertEqual(observed['revision'], revision)
            self.assertNotIn('password', str(native('query_security_groups()')['users']))


if __name__ == '__main__':
    unittest.main()
