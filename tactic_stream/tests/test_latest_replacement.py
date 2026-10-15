"""Native queued check-ins retain latest identity and replace its owned files."""
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image
from pyasm.biz import IconCreator, Snapshot
from pyasm.common import Environment, Xml
from pyasm.command import Trigger
from pyasm.web.api_xmlrpc import ApiXMLRPC
from tactic_stream.server.file_presentation import metadata_paths
import test_checkin_queue


class LatestReplacement(unittest.TestCase):
    setUp = test_checkin_queue.CheckinQueue.setUp
    context = test_checkin_queue.CheckinQueue.context
    submit = test_checkin_queue.CheckinQueue.submit
    options = test_checkin_queue.CheckinQueue.options
    poll = test_checkin_queue.CheckinQueue.poll
    run_one = test_checkin_queue.CheckinQueue.run_one
    snapshots = test_checkin_queue.CheckinQueue.snapshots

    def save(self, identity, sources, **options):
        records = [dict(path=name, size=len(content), file_type=kind) for name, content, kind in sources]
        operation = dict(operation_id=identity, options=dict(self.options(), source_files=records, keep_file_name=False, **options))
        self.submit([operation], [dict(operation_id=identity, file_index=index, offset=0) for index in range(len(sources))], [row[1] for row in sources], chunk=identity)
        self.assertTrue(self.run_one())
        return next(row for row in self.poll()['checkins'] if row['operation_id'] == identity)

    def alias(self):
        with self.context():
            rows = [row for row in self.snapshots() if row['version'] == -1]
            self.assertEqual(len(rows), 1)
            snapshot = Snapshot.get_by_code(rows[0]['code'])
            files = snapshot.get_all_file_objects()
            return dict(code=snapshot.get_code(), xml=snapshot.get_value('snapshot'),
                        files=[file.get_code() for file in files],
                        paths={str(path): Path(path).read_bytes() for file in files for path in metadata_paths(file)})

    def test_binary_files_skip_image_decoder_and_warnings(self):
        with patch.object(IconCreator, '_process_image', autospec=True, side_effect=IconCreator._process_image) as decode, patch.object(Environment, 'add_warning', wraps=Environment.add_warning) as warning:
            result = self.save('toc', [('forest.lodpack.toc', b'binary-content', 'main')], create_icon=True)
        self.assertEqual(result['state'], 'complete', result)
        decode.assert_not_called()
        warning.assert_not_called()
        self.assertEqual(list(self.alias()['paths'].values()), [b'binary-content'])

    def test_media_extensions_and_explicit_preview_reach_native_handlers(self):
        png = io.BytesIO()
        Image.new('RGB', (16, 8), (20, 80, 120)).save(png, format='PNG')
        seen = []
        def video(creator, filename):
            seen.append((filename, Path(creator.file_path).suffix))
        with patch.object(IconCreator, '_process_video', video):
            result = self.save('video', [('clip.mp4', b'video-fixture', 'main')], create_icon=True)
        self.assertEqual(result['state'], 'complete', result)
        self.assertEqual(seen, [('0.mp4', '.mp4')])
        result = self.save('preview', [('model.toc', b'model', 'main'), ('thumb.png', png.getvalue(), 'preview')], create_icon=True)
        self.assertEqual(result['state'], 'complete', result)
        files = self.api.dispatch('query', (self.auth, 'sthpw/file'), dict(filters=[('snapshot_code', result['snapshot']['code'])]))
        self.assertEqual({file['type'] for file in files}, {'main', 'preview', 'web', 'icon'})

    def test_latest_keeps_code_and_numbered_history_with_undo_redo(self):
        first = self.save('first', [('first.toc', b'first', 'main')])
        old = self.alias()
        with patch.object(Trigger, 'call', wraps=Trigger.call) as triggers:
            second = self.save('second', [('second.toc', b'second', 'main')])
        events = [call.args[1] for call in triggers.call_args_list]
        self.assertEqual(events.count('add_file'), 2)
        self.assertIn('delete|sthpw/file', events)
        self.assertNotIn('delete|sthpw/snapshot', events)
        current = self.alias()
        self.assertEqual(current['code'], old['code'])
        self.assertEqual(list(current['paths'].values()), [b'second'])
        with self.context():
            alias = Snapshot.get_by_code(old['code'])
            self.assertEqual(Xml.get_value(alias.get_snapshot_xml(), 'snapshot/@ref_snapshot_code'), second['snapshot']['code'])
        self.assertEqual(sorted(row['version'] for row in self.snapshots() if row['version'] > 0), [1, 2])
        self.api.dispatch('undo', (self.auth,))
        self.assertEqual(self.alias(), old)
        self.api.dispatch('redo', (self.auth,))
        self.assertEqual(self.alias(), current)
        numbered_paths = self.api.dispatch('get_all_paths_from_snapshot', (self.auth, 'sthpw/snapshot?code=' + first['snapshot']['code']))
        self.assertEqual([Path(path).read_bytes() for path in numbered_paths], [b'first'])

    def test_shrinking_group_removes_only_stale_members_and_rollback_restores_latest(self):
        self.save('first', [('beauty.%04d.toc' % index, ('frame%d' % index).encode(), 'main') for index in (1, 3, 5)])
        old = self.alias()
        self.save('second', [('beauty.%04d.toc' % index, ('new%d' % index).encode(), 'main') for index in (1, 3)])
        current = self.alias()
        self.assertEqual(current['code'], old['code'])
        self.assertEqual(len(current['paths']), 2)
        self.assertTrue(all(Path(path).is_file() for path in current['paths']))
        stale = set(old['paths']) - set(current['paths'])
        self.assertEqual(len(stale), 1)
        self.assertTrue(all(not Path(path).exists() for path in stale))
        self.api.dispatch('undo', (self.auth,))
        self.assertEqual(self.alias(), old)
        self.api.dispatch('redo', (self.auth,))
        self.assertEqual(self.alias(), current)
        original = ApiXMLRPC._get_sobject_dict
        def fail(api, sobject, *args, **kwargs):
            if sobject.get_base_search_type() == 'sthpw/snapshot':
                raise ValueError('after latest cleanup')
            return original(api, sobject, *args, **kwargs)
        with patch.object(ApiXMLRPC, '_get_sobject_dict', fail):
            result = self.save('failed', [('different.toc', b'failed', 'main')])
        self.assertEqual(result['state'], 'error')
        self.assertIn('after latest cleanup', result['error'])
        self.assertEqual(self.alias(), current)
        self.assertEqual(len([row for row in self.snapshots() if row['version'] > 0]), 2)

    def test_only_versionless_reuses_alias_without_creating_numbered_snapshot(self):
        for index in range(3):
            result = self.save(str(index), [('latest.toc', str(index).encode(), 'main')], only_versionless=True)
            self.assertEqual(result['state'], 'complete', result)
            self.assertEqual(result['snapshot']['version'], -1)
            if index == 0:
                code = result['snapshot']['code']
            self.assertEqual(result['snapshot']['code'], code)
            self.assertEqual(list(self.alias()['paths'].values()), [str(index).encode()])
        self.assertEqual(len(self.snapshots()), 1)
