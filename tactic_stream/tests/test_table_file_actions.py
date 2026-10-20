"""Snapshot append uses actual files, revisions and the native rollback owner."""
import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch

import test_table_services as fixtures
from test_table_embedded_widgets import write
from pyasm.biz import Snapshot
from pyasm.common import Environment
from pyasm.search import Search
from tactic.ui.table.file_actions import append_snapshot_files


class TableFileActions(unittest.TestCase):
    setUp = fixtures.TableServices.setUp

    def snapshot(self):
        parent = Search.get_by_code('contract/entity', 'A')
        return write(lambda: Snapshot.create(parent, 'file', 'publish', triggers=False))

    def upload(self, name, content=b'new attachment', *, prepared):
        directory = Path(Environment.get_upload_dir()) / prepared['uploadDirectory']
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_bytes(content)
        return path

    def test_append_retains_version_and_registers_the_chosen_file_type(self):
        snapshot = self.snapshot()
        prepared = append_snapshot_files(snapshot.get_search_key())
        self.upload('reference.txt', prepared=prepared)
        result = write(lambda: append_snapshot_files(prepared['searchKey'], action='save', upload_directory=prepared['uploadDirectory'],
            expected_revision=prepared['expectedRevision'], filenames=['reference.txt'],
            file_type='reference', keep_file_name=True))
        self.assertEqual(result['state'], 'saved')
        current = Search.get_by_search_key(prepared['searchKey'])
        self.assertEqual(current.get_value('version'), prepared['version'])
        files = current.get_all_file_objects()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].get_value('type'), 'reference')
        self.assertEqual(Path(current.get_lib_path_by_type('reference')).read_bytes(), b'new attachment')

    def test_revision_conflict_prevents_a_second_write_and_preserves_upload(self):
        snapshot = self.snapshot()
        prepared = append_snapshot_files(snapshot.get_search_key())
        self.upload('first.txt', prepared=prepared)
        arguments = dict(action='save', upload_directory=prepared['uploadDirectory'], expected_revision=prepared['expectedRevision'],
                         keep_file_name=True, filenames=['first.txt'])
        write(lambda: append_snapshot_files(prepared['searchKey'], **arguments))
        second = self.upload('second.txt', prepared=prepared)
        with self.assertRaisesRegex(ValueError, 'Snapshot changed'):
            write(lambda: append_snapshot_files(prepared['searchKey'], **dict(arguments, filenames=['second.txt'])))
        self.assertTrue(second.is_file())
        self.assertEqual(len(Search.get_by_search_key(prepared['searchKey']).get_all_file_objects()), 1)

    def test_all_paths_are_validated_before_appending_the_first_file(self):
        prepared = append_snapshot_files(self.snapshot().get_search_key())
        first = self.upload('safe.txt', prepared=prepared)
        for names in (['safe.txt', '../other.txt'], ['safe.txt', 'missing.txt'], ['safe.txt', 'SAFE.txt']):
            with self.subTest(names=names), self.assertRaises(ValueError):
                write(lambda: append_snapshot_files(prepared['searchKey'], action='save', upload_directory=prepared['uploadDirectory'],
                    expected_revision=prepared['expectedRevision'], filenames=names, keep_file_name=True))
            self.assertTrue(first.is_file())
            self.assertEqual(Search.get_by_search_key(prepared['searchKey']).get_all_file_objects(), [])

    def test_fileundo_rolls_back_a_failure_after_repository_copy(self):
        prepared = append_snapshot_files(self.snapshot().get_search_key())
        self.upload('original.txt', b'keep the existing file', prepared=prepared)
        write(lambda: append_snapshot_files(prepared['searchKey'], action='save', upload_directory=prepared['uploadDirectory'],
            expected_revision=prepared['expectedRevision'], filenames=['original.txt'], keep_file_name=True))
        prepared = append_snapshot_files(prepared['searchKey'])
        source = self.store.data_dir / 'local-original.txt'
        source.write_bytes(b'keep the local source')
        self.upload('rollback.txt', source.read_bytes(), prepared=prepared)
        repository = Path(Environment.get_asset_dir())
        before = {item: hashlib.sha256(item.read_bytes()).digest() for item in repository.rglob('*') if item.is_file()}
        with patch.object(Snapshot, 'update_versionless', side_effect=RuntimeError('late failure')):
            with self.assertRaisesRegex(RuntimeError, 'late failure'):
                write(lambda: append_snapshot_files(prepared['searchKey'], action='save', upload_directory=prepared['uploadDirectory'],
                    expected_revision=prepared['expectedRevision'], filenames=['rollback.txt'], keep_file_name=True))
        self.assertTrue(source.is_file())
        self.assertEqual(source.read_bytes(), b'keep the local source')
        self.assertEqual(append_snapshot_files(prepared['searchKey'])['expectedRevision'], prepared['expectedRevision'])
        after = {item: hashlib.sha256(item.read_bytes()).digest() for item in repository.rglob('*') if item.is_file()}
        self.assertEqual(after, before)

    def test_command_envelope_and_snapshot_projection(self):
        from tactic.ui.table import TableSnapshotAppendCmd
        from pyasm.widget import FileAppendLinkTableElement
        from tactic_stream.server.table_cells import describe_cell
        snapshot = self.snapshot()
        command = TableSnapshotAppendCmd(search_key=snapshot.get_search_key())
        command.execute()
        self.assertEqual(command.info['searchKey'], snapshot.get_search_key())
        widget = FileAppendLinkTableElement()
        widget.set_sobject(snapshot)
        cell = widget.get_cell_value()
        self.assertEqual(cell['projectCode'], 'one')
        self.assertEqual(cell['actions'][0]['name'], 'file-append')
        self.assertTrue(describe_cell(dict(name='append', display=dict(
            handler='FileAppendLinkTableElement',options={}),action=dict(handler='',options={})), {})['supported'])

    def test_api_command_saves_the_prepared_revision_in_its_transaction(self):
        snapshot = self.snapshot()
        ticket = self.api.get_ticket('admin', 'service-cell-fixture')
        prepared = self.api.execute_cmd(ticket, 'tactic.ui.table.TableSnapshotAppendCmd',
            dict(search_key=snapshot.get_search_key()))['info']
        self.upload('api.txt', b'API attachment', prepared=prepared)
        result = self.api.execute_cmd(ticket, 'tactic.ui.table.TableSnapshotAppendCmd',
            dict(action='save', upload_directory=prepared['uploadDirectory'],search_key=prepared['searchKey'],expected_revision=prepared['expectedRevision'],
                filenames=['api.txt'],file_type='reference',keep_file_name=True))
        self.assertEqual(result['info']['state'], 'saved')
        saved = Search.get_by_search_key(prepared['searchKey'])
        self.assertEqual(saved.get_value('version'), prepared['version'])
        self.assertEqual(Path(saved.get_lib_path_by_type('reference')).read_bytes(), b'API attachment')

    def test_permissions_and_project_are_checked_before_file_work(self):
        key = self.snapshot().get_search_key()
        with patch.object(Environment.get_security(), 'is_admin', return_value=False):
            with self.assertRaises(PermissionError):
                append_snapshot_files(key)
        with patch('pyasm.biz.Project.get_project_code', return_value='another'):
            with self.assertRaisesRegex(ValueError, 'own project'):
                append_snapshot_files(key)
        with self.assertRaisesRegex(ValueError, 'requires a snapshot'):
            append_snapshot_files('contract/entity?project=one&code=A')

    def test_invalid_options_never_consume_uploads(self):
        prepared = append_snapshot_files(self.snapshot().get_search_key())
        uploaded = self.upload('valid.txt', prepared=prepared)
        arguments = dict(action='save', upload_directory=prepared['uploadDirectory'], expected_revision=prepared['expectedRevision'],
                         filenames=['valid.txt'], keep_file_name=True)
        for changes in (dict(file_type=''), dict(file_type='a\nb'), dict(keep_file_name='false')):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                write(lambda: append_snapshot_files(prepared['searchKey'], **dict(arguments, **changes)))
            self.assertTrue(uploaded.is_file())
            self.assertEqual(Search.get_by_search_key(prepared['searchKey']).get_all_file_objects(), [])

    def test_current_and_latest_aliases_prepare_their_own_concrete_version(self):
        parent = Search.get_by_code('contract/entity','A')
        current = write(lambda: Snapshot.create(parent,'file','publish',is_current=True,triggers=False))
        latest = write(lambda: Snapshot.create(parent,'file','publish',is_current=False,triggers=False))
        for mode,target in (('current',current),('latest',latest)):
            with self.subTest(mode=mode):
                alias=write(lambda:Snapshot.get_versionless(parent.get_search_type(),parent.get_code(),'publish',mode=mode))
                prepared=append_snapshot_files(alias.get_search_key())
                self.assertEqual(prepared['searchKey'],target.get_search_key())
                self.assertEqual(prepared['version'],target.get_value('version'))
                with self.assertRaisesRegex(ValueError,'concrete snapshot'):
                    write(lambda:append_snapshot_files(alias.get_search_key(),action='save'))

    def test_level_alias_never_switches_to_the_unscoped_latest(self):
        parent = Search.get_by_code('contract/entity','A')
        level = Search.get_by_code('contract/entity','B')
        scoped = write(lambda: Snapshot.create(parent,'file','publish',level_type=level.get_search_type(),
            level_id=level.get_id(),triggers=False))
        self.snapshot()
        alias=write(lambda:Snapshot._get_versionless(parent.get_search_type(),parent.get_code(),'publish','latest',
            True,level_type=level.get_search_type(),level_id=level.get_id()))
        self.assertEqual(append_snapshot_files(alias.get_search_key())['searchKey'],scoped.get_search_key())

    def test_interleaved_sessions_do_not_replace_each_others_same_named_uploads(self):
        first = self.snapshot()
        parent = Search.get_by_code('contract/entity', 'B')
        second = write(lambda: Snapshot.create(parent, 'file', 'publish', triggers=False))
        sessions = [append_snapshot_files(snapshot.get_search_key()) for snapshot in (first, second)]
        self.assertNotEqual(sessions[0]['uploadDirectory'], sessions[1]['uploadDirectory'])
        for prepared, data in zip(sessions, (b'first session', b'second session')):
            self.upload('same.txt', data, prepared=prepared)
        for prepared in sessions:
            write(lambda: append_snapshot_files(prepared['searchKey'], action='save',
                upload_directory=prepared['uploadDirectory'], expected_revision=prepared['expectedRevision'],
                filenames=['same.txt'], keep_file_name=True))
        for prepared, data in zip(sessions, (b'first session', b'second session')):
            snapshot=Search.get_by_search_key(prepared['searchKey'])
            self.assertEqual(Path(snapshot.get_lib_path_by_type('attachment')).read_bytes(), data)

    def test_upload_namespace_cannot_escape_the_ticket_directory(self):
        prepared=append_snapshot_files(self.snapshot().get_search_key())
        uploaded=self.upload('safe.txt', prepared=prepared)
        for directory in ('', '../other', prepared['uploadDirectory']+'/../other', 'D:/other'):
            with self.subTest(directory=directory), self.assertRaisesRegex(ValueError, 'attachment session'):
                write(lambda: append_snapshot_files(prepared['searchKey'], action='save',
                    upload_directory=directory, expected_revision=prepared['expectedRevision'], filenames=['safe.txt']))
        self.assertTrue(uploaded.is_file())
        self.assertEqual(Search.get_by_search_key(prepared['searchKey']).get_all_file_objects(), [])
