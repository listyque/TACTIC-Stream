"""Snapshot append uses actual files, revisions and the native rollback owner."""
import unittest
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import test_table_services as fixtures
from test_table_embedded_widgets import write
from pyasm.biz import Snapshot
from pyasm.common import Environment
from pyasm.search import Search
from tactic.ui.table.file_actions import append_snapshot_files, read_snapshot_files


class TableFileActions(unittest.TestCase):
    setUp = fixtures.TableServices.setUp

    def test_checkin_log_owner_captions_keep_names_codes_and_missing_references(self):
        from tactic.ui.table.snapshot_element_wdg import SnapshotInfoWdg
        from tactic_stream.server.table_cells import WIDGETS
        parent = Search.get_by_code('contract/entity', 'A')
        parent.set_value('name', 'Robot')
        write(parent.commit)
        first = self.snapshot()
        second = self.snapshot()
        second.set_value('search_id', -1)
        write(second.commit)
        missing = self.snapshot()
        missing.set_value('search_id', 999999)
        missing.set_value('search_code', '')
        write(missing.commit)
        widget = SnapshotInfoWdg(name='code')
        widget.set_sobjects([first, second, missing])
        with patch.object(Search, 'get_by_id', wraps=Search.get_by_id) as read:
            widget.preprocess()
        self.assertEqual(read.call_count, 1)
        values = []
        for index in range(3):
            widget.set_current_index(index)
            values.append(widget.get_text_value())
        self.assertEqual(values, ['Robot-A', 'Robot-A', 'n/a'])
        self.assertNotIn('pyasm.prod.web.SnapshotInfoWdg', WIDGETS)

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

    def test_snapshot_files_hidden_row_reads_exact_file_links_in_both_clients(self):
        import ast
        from tactic.ui.table.nested_scope import nested_cell, read_nested_scope
        from tactic.ui.table.nested_table import NestedTableReadCmd
        from tactic.ui.table.snapshot_element_wdg import SnapshotFileElementWdg

        snapshot = self.snapshot()
        prepared = append_snapshot_files(snapshot.get_search_key())
        self.upload('reference.txt', prepared=prepared)
        write(lambda: append_snapshot_files(prepared['searchKey'], action='save',
            upload_directory=prepared['uploadDirectory'], expected_revision=prepared['expectedRevision'],
            filenames=['reference.txt'], file_type='reference', keep_file_name=True))
        snapshot = Search.get_by_search_key(prepared['searchKey'])
        empty = self.snapshot()
        options = dict(dynamic_class='tactic.ui.checkin.SnapshotFilesWdg')
        cell = nested_cell(snapshot.get_search_key(), options)
        scope = cell['nestedTable']
        self.assertFalse(scope['insert'])
        self.assertFalse(scope['selection'])
        self.assertFalse(scope['gear'])
        arguments = dict(parent_key=scope['parentKey'], search_type=scope['searchType'], view=scope['view'])
        result = NestedTableReadCmd(**arguments).execute()
        self.assertEqual(len(result['records']), 1)
        file = snapshot.get_all_file_objects()[0]
        key = file.get_search_key()
        self.assertEqual(result['cells'][key]['file_name']['href'], file.get_web_path())
        self.assertIn('reference.txt', result['cells'][key]['file_name']['text'])
        self.assertFalse(any(value.get('error') for value in result['cells'][key].values()))
        self.assertEqual(read_nested_scope(**dict(arguments, parent_key=empty.get_search_key()))['records'], [])
        self.assertEqual(read_nested_scope(**dict(arguments, filters=[['file_name', '=', 'missing.txt']]))['records'], [])

        handler = Path(__file__).resolve().parents[3] / 'TH'
        text = (handler / 'thlib/ui/table/requests.py').read_text(encoding='utf-8-sig')
        function = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == 'read_nested_scope')
        namespace = {}
        exec(ast.get_source_segment(text, function), namespace)
        self.assertEqual(namespace['read_nested_scope'](**arguments)['records'], result['records'])
        text = (handler / 'thlib/tactic_query.py').read_text(encoding='utf-8-sig')
        function = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout')
        namespace = dict(server=__import__('tactic_client_lib').TacticServerStub(setup=False))
        exec(ast.get_source_segment(text, function), namespace)
        from tactic_stream.server.interface import read_interface
        from tactic_stream.server.table_cells import read_table_cells
        for view in ('checkin_history', 'log'):
            definition = read_interface('sthpw/snapshot', view)
            if view == 'log':
                self.assertTrue(all(e['cell']['supported'] for e in definition['table']['elements']),
                    [e['name'] for e in definition['table']['elements'] if not e['cell']['supported']])
            history = namespace['query_table_layout']('sthpw/snapshot', [snapshot.get_search_key()], view)
            if isinstance(history, str):
                history = json.loads(history)
            self.assertEqual(history['rows'][snapshot.get_search_key()]['files']['nestedTable'], scope)
            if view == 'log':
                parent = Search.get_by_code('contract/entity', 'A')
                expected = parent.get_name() + '-' + parent.get_code() if parent.get_name() else parent.get_code()
                self.assertEqual(history['rows'][snapshot.get_search_key()]['code']['text'], expected)
                cells = read_table_cells('sthpw/snapshot', view, [snapshot.get_search_key()])
                self.assertEqual(cells[snapshot.get_search_key()]['code']['text'], expected)
        # Original TACTIC widgets have no native cell method; exercise that adapter too.
        with patch.object(SnapshotFileElementWdg, 'get_cell_value', None):
            layout = namespace['query_table_layout']('sthpw/file', [key], 'snapshot_files')
        if isinstance(layout, str):
            layout = json.loads(layout)
        self.assertEqual(layout['rows'][key]['file_name']['href'], file.get_web_path())

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
                self.assertEqual(read_snapshot_files(alias.get_search_key())['__search_key__'], target.get_search_key())
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
        self.assertEqual(read_snapshot_files(alias.get_search_key())['__search_key__'],scoped.get_search_key())

    def test_checkout_reads_the_exact_version_and_uses_existing_encoded_web_paths(self):
        from tactic.ui.table.file_actions import TableSnapshotFilesCmd
        from tactic.ui.table import CheckoutButtonElementWdg
        from tactic_stream.server.table_cells import describe_cell
        snapshot = self.snapshot()
        prepared = append_snapshot_files(snapshot.get_search_key())
        self.upload('reference #.txt', b'captured version', prepared=prepared)
        write(lambda: append_snapshot_files(prepared['searchKey'], action='save', upload_directory=prepared['uploadDirectory'],
            expected_revision=prepared['expectedRevision'], filenames=['reference #.txt'], keep_file_name=True))
        latest = self.snapshot()
        data = read_snapshot_files(snapshot.get_search_key())
        self.assertEqual(data['version'], 1)
        self.assertEqual(data['__files__'][0]['file_name'], 'reference #.txt')
        self.assertEqual(read_snapshot_files(latest.get_search_key())['__files__'], [])
        command = TableSnapshotFilesCmd(search_key=snapshot.get_search_key())
        command.execute()
        self.assertEqual(command.info['snapshot']['__search_key__'], snapshot.get_search_key())
        self.assertIn('%23', command.info['files'][0]['href'])
        self.assertEqual(command.info['files'][0]['filename'], 'reference #.txt')
        widget = CheckoutButtonElementWdg()
        widget.set_sobject(snapshot)
        self.assertEqual(widget.get_cell_value()['actions'][0]['name'], 'file-checkout')
        self.assertFalse(widget.get_cell_value()['requiresDesktop'])
        widget.set_option('transfer_mode', 'copy')
        self.assertTrue(widget.get_cell_value()['requiresDesktop'])
        self.assertTrue(describe_cell(dict(name='checkout', display=dict(
            handler='tactic.ui.table.CheckoutButtonElementWdg', options={}), action=dict(handler='', options={})), {})['supported'])

    def test_checkout_checks_identity_project_and_privacy_before_file_reads(self):
        snapshot = self.snapshot()
        with patch.object(Environment.get_security(), 'is_admin', return_value=False), self.assertRaises(PermissionError):
            read_snapshot_files(snapshot.get_search_key())
        with patch('pyasm.biz.Project.get_project_code', return_value='another'), self.assertRaisesRegex(ValueError, 'own project'):
            read_snapshot_files(snapshot.get_search_key())
        with self.assertRaisesRegex(ValueError, 'requires a snapshot'):
            read_snapshot_files('contract/entity?project=one&code=A')
        def make_private():
            snapshot.set_value('search_type', 'sthpw/message')
            snapshot.commit(triggers=False)
        write(make_private)
        with self.assertRaisesRegex(ValueError, 'Messages'):
            read_snapshot_files(snapshot.get_search_key())

    def test_dependency_file_is_captured_and_revision_checked(self):
        from tactic.ui.table.file_actions import TableSnapshotFilesCmd
        snapshot = self.snapshot()
        prepared = append_snapshot_files(snapshot.get_search_key())
        for name in ('one.txt', 'two.txt'):
            self.upload(name, prepared=prepared)
        write(lambda: append_snapshot_files(prepared['searchKey'], action='save', upload_directory=prepared['uploadDirectory'],
            expected_revision=prepared['expectedRevision'], filenames=['one.txt', 'two.txt'], keep_file_name=True))
        fresh = Search.get_by_search_key(prepared['searchKey'])
        revision = hashlib.sha256(json.dumps(fresh.get_data(), sort_keys=True, default=str).encode()).hexdigest()
        file = fresh.get_all_file_objects()[0]
        data = read_snapshot_files(fresh.get_search_key(), file_code=file.get_code(), expected_revision=revision)
        self.assertEqual([row['code'] for row in data['__files__']], [file.get_code()])
        command = TableSnapshotFilesCmd(search_key=fresh.get_search_key(), file_code=file.get_code(), expected_revision=revision)
        command.execute()
        self.assertEqual([row['code'] for row in command.info['files']], [file.get_code()])
        other = next(row for row in fresh.get_all_file_objects() if row.get_code() != file.get_code())
        def sequence():
            other.set_value('file_range', '1-10000000')
            other.commit(triggers=False)
        write(sequence)
        with patch('pyasm.biz.FileGroup.expand_paths', side_effect=AssertionError('Unrelated sequence expanded')):
            command.execute()
        self.assertEqual([row['code'] for row in command.info['files']], [file.get_code()])
        with self.assertRaisesRegex(LookupError, 'file is no longer'):
            read_snapshot_files(fresh.get_search_key(), file_code='other')
        with self.assertRaisesRegex(ValueError, 'Dependencies changed'):
            read_snapshot_files(fresh.get_search_key(), file_code=file.get_code(), expected_revision='old')

    def test_checkout_expands_sequences_and_udims_from_file_range_and_metadata(self):
        from tactic.ui.table.file_actions import TableSnapshotFilesCmd
        snapshot = self.snapshot()
        prepared = append_snapshot_files(snapshot.get_search_key())
        self.upload('frame.####.exr', prepared=prepared)
        write(lambda: append_snapshot_files(prepared['searchKey'], action='save', upload_directory=prepared['uploadDirectory'],
            expected_revision=prepared['expectedRevision'], filenames=['frame.####.exr'], keep_file_name=True))
        file = Search.get_by_search_key(prepared['searchKey']).get_all_file_objects()[0]
        for file_range, metadata, expected in (
            ('1001-1002', {}, ['frame.1001.exr', 'frame.1002.exr']),
            ('', dict(new_template='tex.$UDIM.exr', type='udim', udims=[1001, 1002]), ['tex.1001.exr', 'tex.1002.exr']),
            ('', dict(new_template='shot.$FRAME.exr', type='sequence', frameranges=[(1001, 1002, 4)]), ['shot.1001.exr', 'shot.1002.exr']),
        ):
            with self.subTest(file_range=file_range, metadata=metadata):
                def make_group():
                    file.set_value('file_range', file_range)
                    file.set_value('metadata', json.dumps(metadata))
                    file.commit(triggers=False)
                write(make_group)
                data = read_snapshot_files(snapshot.get_search_key())
                self.assertEqual([item['file_name'] for item in data['__files__'][0]['__member_files__']], expected)
                cmd = TableSnapshotFilesCmd(search_key=snapshot.get_search_key())
                cmd.execute()
                self.assertEqual([item['filename'] for item in cmd.info['files'][0]['members']], expected)
        def make_huge():
            file.set_value('file_range', '1-5001')
            file.set_value('metadata', '{}')
            file.commit(triggers=False)
        write(make_huge)
        with self.assertRaisesRegex(ValueError, 'exceeds the checkout limit'):
            read_snapshot_files(snapshot.get_search_key())

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

    def test_sequence_preview_expands_only_the_first_frame(self):
        from pyasm.biz import FileGroup
        from pyasm.widget import ThumbWdg
        snapshot = self.snapshot()
        prepared = append_snapshot_files(snapshot.get_search_key())
        self.upload('frame.####.exr', prepared=prepared)
        write(lambda: append_snapshot_files(prepared['searchKey'], action='save', upload_directory=prepared['uploadDirectory'],
            expected_revision=prepared['expectedRevision'], filenames=['frame.####.exr'], keep_file_name=True))
        snapshot = Search.get_by_search_key(prepared['searchKey'])
        file = snapshot.get_all_file_objects()[0]
        def make_group():
            file.set_value('file_range', '1001-10000000')
            file.commit(triggers=False)
        write(make_group)
        expand = FileGroup.expand_paths
        def bounded(path, file_range):
            self.assertEqual(file_range.get_num_frames(), 1, 'A preview must not expand the entire sequence')
            return expand(path, file_range)
        widget = ThumbWdg(name='preview')
        widget.set_sobjects([snapshot])
        widget.preprocess()
        widget.set_current_index(0)
        with patch.object(FileGroup, 'expand_paths', side_effect=bounded):
            cell = widget.get_cell_value()
        self.assertTrue(cell['files'][0]['href'].endswith('frame.1001.exr'))
