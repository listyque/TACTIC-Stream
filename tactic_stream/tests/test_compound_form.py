import shutil
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import zipfile

import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store


class CompoundForm(read_tests.ReadParity):
    test_expressions_and_sql_remain_explicitly_unsupported = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import workflow_form_contract, upload_form_contract, compound_form_contract
        with cls.store.connection(write=True) as db:
            workflow_form_contract.install_fixture(db)
            upload_form_contract.install_fixture(db)
            compound_form_contract.install_fixture(db)
        cls.cases = [dict(method='compound_form_contract', name=operation, operation=operation, project='one')
                     for operation in ('zip_prepare', 'zip_fresh', 'zip_edit', 'time_actions', 'time_only')]

    def new_result(self, case):
        import compound_form_contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                self.api.auth.bind_security('admin', self.ticket)
                return compound_form_contract.run(case)

    def assert_case_result(self, case, result, original):
        if case['operation'] == 'zip_edit':
            self.assertEqual(original['error'], 'FileNotFoundError')
            self.assertEqual([row[:3] for row in result], [['PARENT', 1, 'Two objects from ZIP'], ['SECOND', 1, 'Two objects from ZIP']])
            self.assertEqual([len(row[3]) for row in result], [2, 1])
        elif case['operation'] == 'zip_fresh':
            self.assertEqual([[row[0], len(row[1])] for row in original], [['PARENT', 1], ['PARENT', 1], ['SECOND', 1]])
            self.assertEqual([[row[0], len(row[1])] for row in result], [['PARENT', 2], ['SECOND', 1]])
        elif case['operation'] == 'time_only':
            # Original attaches today's date to a SQL time value; native preserves its actual type.
            self.assertRegex(original, r'^\d{4}-\d{2}-\d{2} ')
            self.assertEqual(result, '06:45:00')
        else:
            if case['operation'] == 'time_actions':
                self.assertTrue(original.pop('python3_alias_needed'))
                self.assertFalse(result.pop('python3_alias_needed'))
                self.assertEqual(original['dates'][1], '2027-02-04 15:20:25')
                self.assertEqual(result['dates'][1], '2027-02-04 15:20:25.125000')
                original['dates'][1] = result['dates'][1]
            self.assertEqual(result, original)

    def test_zip_guards_handoff_and_batch_rollback(self):
        import compound_form_contract
        from pyasm.command import Command, MultiZipUploadAction
        from pyasm.common import Common, Environment, TacticException
        from pyasm.common.errors import SecurityException
        from pyasm.search import Search
        from pyasm.web import WebContainer
        from tactic.ui.panel import EditCmd
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                self.api.auth.bind_security('admin', self.ticket)
                result = compound_form_contract.run(dict(operation='zip_handoff'))
                self.assertEqual([len(row[3]) for row in result], [2, 1])
                upload_dir = Path(Environment.get_upload_dir())
                self.assertFalse(any(upload_dir.iterdir()))
                web = WebContainer.get_web()
                revision = upload_dir / 'revision.zip'
                revision.write_bytes(compound_form_contract.archive_payload())
                web.set_form_value('edit|attachments0|path', revision.name)
                web.set_form_value('edit|attachments|is_revision', 'on')
                cmd = EditCmd(search_key=compound_form_contract.KEY, view=compound_form_contract.VIEW, element_names=['attachments'])
                cmd.get_transaction().set_sync(False)
                Command.execute_cmd(cmd)
                search = Search('sthpw/snapshot')
                search.add_filter('context', 'archive')
                search.add_filter('version', 0, '>')
                self.assertEqual(sorted((obj.get_value('search_code'), obj.get_version(), obj.get_value('revision')) for obj in search.get_sobjects()),
                                 [('PARENT', 1, 0), ('PARENT', 1, 1), ('SECOND', 1, 0), ('SECOND', 1, 1)])
                web.params.clear()
                path = upload_dir / 'rollback.zip'
                payload = compound_form_contract.archive_payload()
                path.write_bytes(payload)
                web.set_form_value('edit|attachments0|path', path.name)
                web.set_form_value('edit|attachments0|ticket', Environment.get_ticket())
                web.set_form_value('edit|attachments|context', 'failed_archive')
                before = Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()
                original = MultiZipUploadAction.postprocess
                def fail(action):
                    original(action)
                    raise ValueError('Late batch failure')
                cmd = EditCmd(search_key=compound_form_contract.KEY, view=compound_form_contract.VIEW, element_names=['attachments'])
                cmd.get_transaction().set_sync(False)
                with patch.object(MultiZipUploadAction, 'postprocess', fail), self.assertRaises(ValueError):
                    Command.execute_cmd(cmd)
                self.assertEqual((Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()), before)
                self.assertEqual(path.read_bytes(), payload)
                # Validate every ZIP path before touching the destination.
                for names, error in [(['../outside.txt'], SecurityException), (['C:/outside.txt'], SecurityException),
                                     (['folder\\outside.txt'], SecurityException), (['same.txt', 'SAME.txt'], TacticException),
                                     (['file', 'file/child.txt'], TacticException), (['link'], SecurityException),
                                     (['bad\0name'], SecurityException)]:
                    buffer = BytesIO()
                    with zipfile.ZipFile(buffer, 'w') as archive:
                        for name in names:
                            item = zipfile.ZipInfo('raw')
                            item.filename = item.orig_filename = name
                            if name == 'link':
                                import stat
                                item.external_attr = stat.S_IFLNK << 16
                            archive.writestr(item, b'unsafe')
                    path.write_bytes(buffer.getvalue())
                    destination = upload_dir / 'unsafe_extract'
                    cmd = Command()
                    cmd.execute = lambda: Common.unzip_file(str(path), str(destination))
                    cmd.get_transaction().set_sync(False)
                    with self.assertRaises(error):
                        Command.execute_cmd(cmd)
                    self.assertFalse(destination.exists())
                action = MultiZipUploadAction()
                action.set_option('naming', "__import__('os').system('bad')")
                cmd = Command()
                cmd.execute = action.check
                cmd.get_transaction().set_sync(False)
                with self.assertRaises(ValueError):
                    Command.execute_cmd(cmd)
                # An exaggerated ZIP header is rejected before allocating/extracting its contents.
                buffer = BytesIO()
                with zipfile.ZipFile(buffer, 'w') as archive:
                    archive.writestr('large.txt', b'small payload')
                payload = bytearray(buffer.getvalue())
                import struct
                offset = payload.index(b'PK\x01\x02')
                struct.pack_into('<I', payload, offset + 24, 512 * 1024 * 1024 + 1)
                path.write_bytes(payload)
                cmd = Command()
                cmd.execute = lambda: Common.unzip_file(str(path), str(destination))
                cmd.get_transaction().set_sync(False)
                with self.assertRaises(TacticException):
                    Command.execute_cmd(cmd)
                self.assertFalse(destination.exists())

    def test_time_descriptors_and_invalid_edit_roll_back(self):
        import compound_form_contract
        from pyasm.command import Command
        from pyasm.search import Search
        from pyasm.web import WebContainer
        from tactic.ui.panel import EditCmd
        from tactic_stream.server.interface import read_form
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                self.api.auth.bind_security('admin', self.ticket)
                compound_form_contract.setup()
                form = read_form('contract/work_item', compound_form_contract.VIEW, compound_form_contract.KEY)
                field = next(field for field in form['fields'] if field['name'] == 'clock')
                self.assertEqual(field['values'], ['08:30:15.250000'])
                self.assertEqual(field['input'], dict(type='time', value='08:30', unchanged_value='08:30:15.250000'))
                web = WebContainer.get_web()
                web.set_form_value('edit|name', 'Must roll back')
                web.set_form_value('edit|clock', 'invalid time')
                cmd = EditCmd(search_key=compound_form_contract.KEY, view=compound_form_contract.VIEW, element_names=['name', 'clock'])
                cmd.get_transaction().set_sync(False)
                with self.assertRaises(ValueError):
                    Command.execute_cmd(cmd)
                self.assertEqual(Search.get_by_search_key(compound_form_contract.KEY).get_value('name'), 'Parent')
