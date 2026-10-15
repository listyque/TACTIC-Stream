"""Native multi-group permissions: revisions, cycles, ACLs and atomic rollback."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.common import Config
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.storage import Store
from pyasm.search.search import RequestContext, request_context
from pyasm.security import LoginGroup
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.security_rules import security_rules_request as request
from tactic_stream.server.widget_configuration import WidgetConfigConflict


def exercise(store):
    check = unittest.TestCase(); api = Api(store); ticket = api.get_ticket('admin', 'rules-test-password')
    auth = dict(ticket=ticket, project='admin')
    for name in ('team', 'reviewers'):
        api.dispatch('insert', (auth, 'sthpw/login_group', dict(login_group=name, description=name, access_level='none')))
    with request_context(RequestContext(store, 'admin', 'admin')):
        api.auth.bind_security('admin', ticket)
        catalog = request('read', dict(project='admin'))
        groups = {row['label']: row['identity'] for row in catalog['metadata']['groups']}
        check.assertNotIn('admin', groups)
        check.assertTrue(catalog['metadata']['globalDefaultRulesByLevel'])
        document = deepcopy(catalog['document'])
        document['groups'][groups['team']]['xml'] = '<rules note="preserved"><!--custom--><rule group="project" code="admin" access="allow"/><rule group="link" element="*" project="admin" access="view"/><rule group="custom_scope" key="sample" access="edit"/></rules>'
        document['groups'][groups['team']]['subGroups'] = 'reviewers'
        saved = request('save', dict(project='admin', document=document, expected_revision=catalog['revision']))
        check.assertEqual(saved['document'], document)
        with check.assertRaises(WidgetConfigConflict):
            request('save', dict(project='admin', document=document, expected_revision=catalog['revision']))
        check.assertEqual(request('save', dict(project='admin', document=document, expected_revision=saved['revision']))['revision'], saved['revision'])
        def save(data): return request('save', dict(project='admin', document=data, expected_revision=saved['revision']))
        cycle = deepcopy(document); cycle['groups'][groups['reviewers']]['subGroups'] = 'team'
        with check.assertRaisesRegex(ValueError, 'cycle'): save(cycle)
        for xml in ('<rules>', '<other/>', '<!DOCTYPE rules><rules/>', '<rules><rule group="project" access="invalid"/></rules>'):
            bad = deepcopy(document); bad['groups'][groups['reviewers']]['xml'] = xml
            with check.assertRaises(ValueError): save(bad)
        # Failed second commit must roll back the first group's permission write.
        changed = deepcopy(document)
        for data in changed['groups'].values(): data['project'] = 'admin'
        original = LoginGroup.commit; calls = []
        def fail_second(group, *args, **kwargs):
            calls.append(group.get_code())
            if len(calls) == 2: raise ValueError('late failure')
            return original(group, *args, **kwargs)
        with patch.object(LoginGroup, 'commit', fail_second), check.assertRaisesRegex(ValueError, 'late failure'): save(changed)
        check.assertEqual(request('read', dict(project='admin'))['document'], document)
        malformed = deepcopy(document); malformed['groups'][groups['team']]['password'] = 'forbidden'
        with check.assertRaises(ValueError): save(malformed)
        for row in Search('sthpw/login_group').get_sobjects():
            if row.get_value('login_group') == 'team': check.assertEqual(row.get_value('description'), 'team')
        with patch.object(api.auth.bind_security('admin', ticket), 'is_admin', return_value=False):
            for action in ('read', 'save'):
                with check.assertRaises(SecurityException): request(action, dict(project='admin'))


class SecurityRules(unittest.TestCase):
    def test_permissions_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config(); store = Store(root / 'sqlite')
                store.initialize(hash_password('rules-test-password')); exercise(store)
            if not os.environ.get('STREAM_POSTGRES_HOST'): return
            import uuid
            import psycopg
            from psycopg import sql
            from xml.etree.ElementTree import Element, SubElement, tostring
            credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'], port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                user=os.environ.get('STREAM_POSTGRES_USER', 'stream'), password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
            database = 'stream_rules_' + uuid.uuid4().hex[:12]
            config = Element('config', version='2'); section = SubElement(config, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database, password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'],
                **{key: value for key, value in credentials.items() if key != 'password'}).items(): SubElement(section, key).text = value
            path = root / 'tactic-conf.xml'; path.write_bytes(tostring(config))
            with psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
                try:
                    with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                        Config.reload_config(); store = Store(root / 'postgres')
                        store.initialize(hash_password('rules-test-password')); exercise(store)
                finally:
                    maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(database)))
                    Config.reload_config()


if __name__ == '__main__': unittest.main()
