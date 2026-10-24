"""Durable naming apply and real file collision checks on owned databases."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
from xmlrpc.client import Binary

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]

from pyasm.common import Config
from pyasm.common.errors import UserException
from pyasm.search.sql import Sql
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from tools.checkin_benchmark import prepare

COMMAND = 'tactic.ui.panel.naming_cmd.NamingCmd'


class NamingApply(unittest.TestCase):
    database_config = ''

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='naming-apply-')
        self.addCleanup(self.temp.cleanup)
        environment = patch.dict(os.environ, {'TACTIC_CONFIG_PATH': self.database_config, 'TACTIC_TMP_CONFIG_PATH': ''})
        environment.start()
        self.addCleanup(environment.stop)
        Config.reload_config()
        self.addCleanup(Config.reload_config)
        self.store = Store(Path(self.temp.name) / 'data')
        self.api, ticket = prepare(self.store)
        self.auth = dict(ticket=ticket, project='one')
        self.sample = dict(key='cg/shot?project=one&code=SH001', file='source.bin',
                           process='agent_native', context='agent_native/main')
        self.document = dict(search_type='cg/shot', context='agent_native/*', checkin_type='strict',
                             dir_naming='{project.code}/agent_native', file_naming='fixed.bin')

    def call(self, action, **kwargs):
        return Api(self.store).dispatch('execute_cmd', (self.auth, COMMAND, dict(
            action=action, project_code='one', search_type='cg/shot', **kwargs)))['info']

    def test_atomic_replay_aba_concurrency_and_collision(self):
        original = self.call('load')
        self.store.upgrade()
        self.assertEqual(self.call('load')['revision'], original['revision'])
        arguments = dict(document=self.document, sample=self.sample, expected_revision=original['revision'],
                         operation_id=str(uuid4()))
        with ThreadPoolExecutor(max_workers=2) as workers:
            receipts = list(workers.map(lambda _: self.call('apply', **arguments), range(2)))
        self.assertEqual(receipts[0], receipts[1])
        receipt = receipts[0]
        self.assertEqual(sum(row['identity'] == receipt['identity'] for row in self.call('load')['rules']), 1)
        # A fresh Api/Store owns no in-memory deduplication state.
        self.store = Store(self.store.data_dir)
        self.assertEqual(self.call('apply', **arguments), receipt)
        self.assertEqual(self.call('operation', operation_id=arguments['operation_id']), receipt)
        with self.assertRaisesRegex(UserException, 'different request'):
            self.call('apply', **dict(arguments, document=dict(self.document, file_naming='different.bin')))

        # Native API commits with triggers=False still change the database revision.
        before_aba = self.call('load')
        self.api.dispatch('update', (self.auth, receipt['key'], {'file_naming': 'temporary.bin'}), {'triggers': False})
        self.api.dispatch('update', (self.auth, receipt['key'], {'file_naming': 'fixed.bin'}), {'triggers': False})
        after_aba = self.call('load')
        self.assertEqual(before_aba['rules'], after_aba['rules'])
        self.assertNotEqual(before_aba['revision'], after_aba['revision'])
        with self.assertRaisesRegex(UserException, 'changed on the server'):
            self.call('apply', **dict(arguments, identity=receipt['identity'], operation_id=str(uuid4()),
                                     expected_revision=before_aba['revision']))

        # Failure between native save and receipt insert rolls both rule and revision back.
        failed_id = str(uuid4())
        update = Sql._do_update
        def fail_receipt(sql, query, *args, **kwargs):
            if query.startswith('INSERT INTO spt_naming_operation'):
                raise ValueError('receipt persistence failed')
            return update(sql, query, *args, **kwargs)
        with patch.object(Sql, '_do_update', fail_receipt):
            with self.assertRaisesRegex(ValueError, 'receipt persistence failed'):
                self.call('apply', **dict(arguments, operation_id=failed_id, identity=receipt['identity'],
                                         expected_revision=after_aba['revision'],
                                         document=dict(self.document, file_naming='failed.bin')))
        self.assertEqual(self.call('load'), after_aba)
        self.assertEqual(self.call('operation', operation_id=failed_id)['status'], 'not_found')

        # Two different operations may not both win against one loaded revision.
        def compete(index):
            try:
                return self.call('apply', **dict(arguments, operation_id=str(uuid4()),
                                                expected_revision=after_aba['revision'], identity=receipt['identity'],
                                                document=dict(self.document, file_naming=f'race_{index}.bin')))
            except UserException as error:
                self.assertIn('changed on the server', str(error))
                return None
        with ThreadPoolExecutor(max_workers=2) as workers:
            competed = list(workers.map(compete, range(2)))
        self.assertEqual(sum(result is not None for result in competed), 1)
        self.api.dispatch('update', (self.auth, receipt['key'], {'file_naming': 'fixed.bin'}))

        source = Path(self.temp.name) / 'source.bin'
        source.write_bytes(b'first object bytes')
        self.api.dispatch('upload_file', (self.auth, source.name, Binary(source.read_bytes())))
        first = self.api.dispatch('simple_checkin', (self.auth, self.sample['key'], self.sample['context'], str(source)),
                                  dict(mode='upload', create_icon=False, checkin_type='strict'))
        file = first['__file_sobjects__'][0]
        destination = Path(file['checkin_dir']) / file['file_name']
        self.assertEqual(destination.read_bytes(), source.read_bytes())
        other = self.api.dispatch('insert', (self.auth, 'cg/shot', dict(code='SH002', name='Another shot', scenes_code='EP001')))
        source.write_bytes(b'second object bytes')
        self.api.dispatch('upload_file', (self.auth, source.name, Binary(source.read_bytes())))
        before_files = self.api.dispatch('query', (self.auth, 'sthpw/file'))
        with self.assertRaises(Exception) as collision:
            self.api.dispatch('simple_checkin', (self.auth, other['__search_key__'], self.sample['context'], str(source)),
                              dict(mode='upload', create_icon=False, checkin_type='strict'))
        self.assertRegex(str(collision.exception).lower(), 'exist|collision|overwrite|belong')
        self.assertEqual(destination.read_bytes(), b'first object bytes')
        self.assertEqual(source.read_bytes(), b'second object bytes')
        self.assertEqual(self.api.dispatch('query', (self.auth, 'sthpw/file')), before_files)

        # A historical receipt never resurrects a subsequently deleted rule.
        self.api.dispatch('delete_sobject', (self.auth, receipt['key']))
        deleted = self.call('load')
        self.assertEqual(self.call('apply', **arguments), receipt)
        self.assertEqual(self.call('load'), deleted)


if __name__ == '__main__':
    if '--postgres' in sys.argv:
        from tools.file_project_checks import postgres
        sys.argv.remove('--postgres')
        with postgres() as config:
            NamingApply.database_config = config
            result = unittest.main(exit=False)
        raise SystemExit(not result.result.wasSuccessful())
    unittest.main()
