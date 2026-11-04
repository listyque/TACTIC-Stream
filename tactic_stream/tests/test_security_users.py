"""Native Handler user lifecycle, credentials, conflicts, permissions and rollback."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.common import Config
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security import Login
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.security_users import security_users_request as request
from tactic_stream.server.widget_configuration import WidgetConfigConflict


def exercise(store):
    check = unittest.TestCase(); api = Api(store)
    ticket = api.get_ticket('admin', 'user-test-admin')
    with request_context(RequestContext(store, login='admin', project='sthpw')):
        api.auth.bind_security('admin', ticket)
        group = SearchType.create('sthpw/login_group'); group.set_value('login_group', 'people'); group.commit()
        other = SearchType.create('sthpw/login_group'); other.set_value('login_group', 'other'); other.commit()
        document = {field: '' for field in request('read', {})['fields']}
        document.update(login='alice', display_name='Alice', password='initial-password', email='alice@example.test', groups=['people'], s_status='')
        catalog = request('save', dict(document=document))
        user = next(row for row in catalog['users'] if row['login'] == 'alice')
        check.assertEqual(user['document']['groups'], ['people'])
        check.assertEqual(user['document']['password'], '')
        check.assertEqual(Login.get_by_login('alice').get_value('upn'), 'alice')
        check.assertNotIn('initial-password', json.dumps(catalog))
        check.assertFalse(any(key in user['document'] for key in ('failure_count', 'ticket', 'license_type')))
        with check.assertRaisesRegex(ValueError, 'already exists'):
            request('save', dict(document=document))
        with check.assertRaisesRegex(ValueError, 'no longer exists'):
            request('save', dict(document={**document, 'login': 'missing_group', 'groups': ['missing']}))
        check.assertIsNone(Search.get_by_code('sthpw/login', 'missing_group'))
        # All profile, membership and password edits roll back together.
        draft = copy.deepcopy(user['document']); draft.update(display_name='Must rollback', password='new-password', groups=['other'])
        with patch.object(Login, 'set_password', side_effect=ValueError('password failure')):
            with check.assertRaisesRegex(ValueError, 'password failure'):
                request('save', dict(identity='alice', document=draft, expected_revision=user['revision']))
        fresh = next(row for row in request('read', {})['users'] if row['login'] == 'alice')
        check.assertEqual(fresh['document'], user['document'])
        # A concurrent membership write must not disappear on profile save.
        alice = Login.get_by_login('alice'); alice.add_to_group('other')
        with check.assertRaises(WidgetConfigConflict):
            request('save', dict(identity='alice', document=draft, expected_revision=user['revision']))
        user = next(row for row in request('read', {})['users'] if row['login'] == 'alice')
        draft = copy.deepcopy(user['document']); draft.update(display_name='Alice Edited', password='new-password', groups=['other'], hourly_wage=0)
        catalog = request('save', dict(identity='alice', document=draft, expected_revision=user['revision']))
        user = next(row for row in catalog['users'] if row['login'] == 'alice')
        check.assertEqual(user['document']['groups'], ['other']); check.assertEqual(user['document']['display_name'], 'Alice Edited')
        check.assertEqual(user['document']['hourly_wage'], 0)
        json.dumps(catalog)  # Same JSONResponse-compatible types on SQLite and PostgreSQL.
        with check.assertRaisesRegex(ValueError, 'cannot be changed'):
            request('save', dict(identity='alice', document={**user['document'], 'login': 'bob'}, expected_revision=user['revision']))
        admin = next(row for row in catalog['users'] if row['login'] == 'admin')
        with check.assertRaisesRegex(ValueError, 'signed in'):
            request('save', dict(identity='admin', document={**admin['document'], 's_status': 'retired'}, expected_revision=admin['revision']))
        with check.assertRaisesRegex(ValueError, 'profile field'):
            request('save', dict(identity='alice', document={**user['document'], 'first_name': []}, expected_revision=user['revision']))
    alice_ticket = api.get_ticket('alice', 'new-password')
    with request_context(RequestContext(store, login='alice', project='sthpw')):
        api.auth.bind_security('alice', alice_ticket)
        for action in ('read', 'save'):
            with check.assertRaises(SecurityException):
                request(action, {})
    with request_context(RequestContext(store, login='admin', project='sthpw')):
        api.auth.bind_security('admin', ticket)
        user = next(row for row in request('read', {})['users'] if row['login'] == 'alice')
        catalog = request('save', dict(identity='alice', document={**user['document'], 's_status': 'retired'}, expected_revision=user['revision']))
        user = next(row for row in catalog['users'] if row['login'] == 'alice')
        check.assertTrue(user['retired'])
        request('save', dict(identity='alice', document={**user['document'], 's_status': ''}, expected_revision=user['revision']))
        check.assertEqual(Search.get_by_code('sthpw/login', 'alice').get_value('s_status'), '')
    with check.assertRaises(Exception):
        api.auth.validate(alice_ticket)
    check.assertTrue(api.get_ticket('alice', 'new-password'))


class SecurityUsers(unittest.TestCase):
    def test_native_user_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config(); store = Store(root / 'sqlite')
                store.initialize(hash_password('user-test-admin')); exercise(store)
            if not os.environ.get('STREAM_POSTGRES_HOST'):
                return
            import uuid
            import psycopg
            from psycopg import sql
            from xml.etree.ElementTree import Element, SubElement, tostring
            credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'], port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                user=os.environ.get('STREAM_POSTGRES_USER', 'stream'), password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
            database = 'stream_users_' + uuid.uuid4().hex[:12]
            config = Element('config', version='2'); section = SubElement(config, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database,
                password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'], **{key: value for key, value in credentials.items() if key != 'password'}).items():
                SubElement(section, key).text = value
            path = root / 'tactic-conf.xml'; path.write_bytes(tostring(config))
            with psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
                try:
                    with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                        Config.reload_config(); store = Store(root / 'postgres')
                        store.initialize(hash_password('user-test-admin')); exercise(store)
                finally:
                    maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(database)))
                    Config.reload_config()


if __name__ == '__main__':
    unittest.main()
