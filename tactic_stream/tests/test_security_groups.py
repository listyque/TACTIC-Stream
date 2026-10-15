"""Handler group creation, native membership deltas, conflict and rollback."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.common import Config
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security import Login
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.security_groups import security_groups_request as request
from tactic_stream.server.widget_configuration import WidgetConfigConflict


def exercise(store):
    check = unittest.TestCase(); api = Api(store)
    ticket = api.get_ticket('admin', 'group-test-password')
    auth = dict(ticket=ticket, project='sthpw', language='python')
    for name in ('alice', 'bob', 'retired'):
        api.dispatch('insert', (auth, 'sthpw/login', dict(login=name, display_name=name.title(),
            password=hash_password('user-test-password'), s_status='retired' if name == 'retired' else '')))
    with request_context(RequestContext(store, login='admin', project='sthpw')):
        api.auth.bind_security('admin', ticket)
        catalog = request('read', {})
        check.assertTrue(next(user for user in catalog['users'] if user['login'] == 'retired')['retired'])
        payload = dict(login_group='team', description='People', add_members=['alice'], remove_members=[])
        saved = request('save', payload)
        group = next(group for group in saved['groups'] if group['code'] == saved['selected'])
        check.assertEqual(group['name'], 'team'); check.assertEqual(group['memberCount'], 1)
        # Retrying the creation cannot create another group or membership.
        again = request('save', payload)
        check.assertEqual(again['selected'], group['code'])
        check.assertEqual(sum(row['name'] == 'team' for row in again['groups']), 1)
        # Concurrent membership changes survive the editor's own deltas.
        bob = Search.get_by_code('sthpw/login', 'bob'); bob.add_to_group('team')
        saved = request('save', dict(group_code=group['code'], login_group='team', description='Edited',
            expected_revision=group['revision'], add_members=['retired'], remove_members=['alice']))
        check.assertEqual({row['login'] for row in saved['memberships'] if row['login_group'] == 'team'}, {'bob', 'retired'})
        fresh = next(row for row in saved['groups'] if row['code'] == group['code'])
        from tactic_stream.server.security_groups import group_revision
        current = Search('sthpw/login_group'); current.add_filter('code', group['code'])
        check.assertEqual(Search.get_by_code('sthpw/login_group', group['code']).get_data(), current.get_sobject().get_data(), 'cached group data')
        check.assertEqual(group_revision(Search.get_by_code('sthpw/login_group', group['code'])), fresh['revision'], 'fresh cached revision')
        with check.assertRaises(WidgetConfigConflict):
            request('save', dict(group_code=group['code'], login_group='team', description='Stale', expected_revision=group['revision']))
        with check.assertRaisesRegex(ValueError, 'cannot be changed'):
            request('save', dict(group_code=group['code'], login_group='renamed', description='', expected_revision=fresh['revision']))
        observed = next(row for row in request('read', {})['groups'] if row['code'] == group['code'])
        check.assertEqual(observed, fresh, 'failed validation must not change group metadata')
        with patch.object(Login, 'add_to_group', side_effect=ValueError('late member failure')):
            with check.assertRaisesRegex(ValueError, 'late member failure'):
                request('save', dict(group_code=group['code'], login_group='team', description='Must rollback',
                    expected_revision=fresh['revision'], add_members=['alice']))
        check.assertEqual(next(row for row in request('read', {})['groups'] if row['code'] == group['code'])['description'], 'Edited')
        with check.assertRaisesRegex(ValueError, 'no longer exist'):
            request('save', dict(login_group='missing_user_team', description='', add_members=['missing']))
        check.assertFalse(any(row['name'] == 'missing_user_team' for row in request('read', {})['groups']))
    alice_ticket = api.get_ticket('alice', 'user-test-password')
    with request_context(RequestContext(store, login='alice', project='sthpw')):
        api.auth.bind_security('alice', alice_ticket)
        for action in ('read', 'save'):
            with check.assertRaises(SecurityException):
                request(action, {})


class SecurityGroups(unittest.TestCase):
    def test_native_groups_membership_conflict_rollback_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config(); store = Store(root / 'sqlite')
                store.initialize(hash_password('group-test-password')); exercise(store)
            if not os.environ.get('STREAM_POSTGRES_HOST'):
                return
            import uuid
            import psycopg
            from psycopg import sql
            from xml.etree.ElementTree import Element, SubElement, tostring
            credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'], port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                user=os.environ.get('STREAM_POSTGRES_USER', 'stream'),
                password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
            database = 'stream_groups_' + uuid.uuid4().hex[:12]
            config = Element('config', version='2'); section = SubElement(config, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database,
                password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'],
                **{key: value for key, value in credentials.items() if key != 'password'}).items():
                SubElement(section, key).text = value
            path = root / 'tactic-conf.xml'; path.write_bytes(tostring(config))
            with psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
                try:
                    with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                        Config.reload_config(); store = Store(root / 'postgres')
                        store.initialize(hash_password('group-test-password')); exercise(store)
                finally:
                    maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(database)))
                    Config.reload_config()


if __name__ == '__main__':
    unittest.main()
