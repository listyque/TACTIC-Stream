"""Native browser preparation and check-in on a private CG template installation."""
import tempfile
import ast
import json
import os
import unittest
from pathlib import Path
from xmlrpc.client import Binary
from unittest.mock import patch

from tools.checkin_benchmark import prepare
from pyasm.search.storage import Store
from pyasm.checkin import FileAppendCheckin, CheckinException
from pyasm.common.errors import SecurityException, UserException
from tactic.command.browser_checkin_cmd import matched_files, DEFAULT_TEMPLATES


class BrowserCheckin(unittest.TestCase):
    def test_web_matching_keeps_its_file_limit(self):
        records = [dict(path='payload_%04d.txt' % index, size=4) for index in range(1001)]
        with self.assertRaisesRegex(UserException, 'up to 1000 files'):
            matched_files(records)
        self.assertEqual(sum(len(indices) for group, indices in matched_files(records, max_files=10000)), 1001)

    def test_unchanged_handler_replaces_all_metadata_group_members(self):
        source = Path('D:/code/th_codex/thlib/tactic_query.py').read_text(encoding='utf8')
        function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'create_snapshot_extended')
        code = ast.get_source_segment(source, function) + '\nreturn create_snapshot_extended(**kwargs["options"])'
        with tempfile.TemporaryDirectory() as temporary:
            self.store = Store(temporary)
            self.api, ticket = prepare(self.store)
            self.api.protocol = 'json'
            self.auth = dict(ticket=ticket, project='one')
            metadata = dict(new_template='$FILENAME.$FRAME.$EXT',new_filename='native_group',new_file_ext='txt',new_padding=4,frameranges=['1','3'])
            for version in (1,2):
                directories = dict(version=f'one/handler-group/v{version}',versionless='one/handler-group/latest')
                paths = {}
                for destination,directory in directories.items():
                    folder = Path(temporary) / 'assets' / directory
                    folder.mkdir(parents=True,exist_ok=True)
                    paths[destination] = [(folder / f'native_group.{frame:04d}.txt').as_posix() for frame in (1,3)]
                    for path in paths[destination]:
                        Path(path).write_bytes(f'Handler version {version}'.encode())
                info = dict(files_types=['main'],file_sizes=[34],version_files=paths['version'][:1],versionless_files=paths['versionless'][:1],
                            version_files_paths=[directories['version']],versionless_files_paths=[directories['versionless']],version_metadata=[metadata],versionless_metadata=[metadata])
                self.api.dispatch('execute_python_script',(self.auth,'',dict(code=code,options=dict(search_key='cg/shot?project=one&code=SH001',context='publish/native-group',
                    project_code='one',files_info=json.dumps(info),mode='inplace',repo_name='default',create_icon=False))))
                self.assertEqual([Path(path).read_bytes() for path in paths['versionless']],[f'Handler version {version}'.encode()] * 2)

    def test_matching_native_shapes_and_sparse_frames(self):
        source = Path('D:/code/th_codex/thlib/global_functions.py').read_text(encoding='utf8')
        from tactic_stream.server import file_matching
        namespace = dict(vars(file_matching))
        nodes = [node for node in ast.parse(source).body if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in ('natural_sort_key','FileObject','MatchTemplate')]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'handler/global_functions.py','exec'),namespace)
        patterns = [*DEFAULT_TEMPLATES,'$FILENAME.$LAYER.$FRAME.$EXT','$FILENAME.$LAYER_$UDIM.$EXT']
        samples = [['beauty.%04d.exr' % frame for frame in (1,2,4,7)],['diffuse_%d.png' % tile for tile in (1001,1002)],
                   ['diffuse_u%d_v1.png' % tile for tile in (1,2)],['beauty.%04d_%d.exr' % (frame,tile) for frame in (1,3) for tile in (1001,1002)],
                   ['beauty.%04d_u%d_v1.exr' % (frame,tile) for frame in (1,3) for tile in (1,2)],
                   ['beauty.layer.%04d.exr' % frame for frame in (1,3)], ['beauty.layer_%d.png' % tile for tile in (1001,1002)],['readme']]
        for paths in samples:
            native = namespace['MatchTemplate'](patterns).get_files_objects(paths)
            migrated = matched_files([dict(path=path,size=1) for path in paths],patterns)
            native_groups = [group for groups in native.values() for group in groups]
            self.assertEqual(len(migrated),len(native_groups))
            for (group,indices),original in zip(migrated,native_groups):
                original.set_sizes_list([1] * len(indices))
                self.assertEqual(json.loads(json.dumps(group.get_metadata())),json.loads(json.dumps(original.get_metadata(),default=list)))
                self.assertEqual(group.get_all_new_files_list(new_filename=('renamed','.','.png'),new_filepath='repo',new_frame_padding=4),
                                 original.get_all_new_files_list(new_filename=('renamed','.','.png'),new_filepath='repo',new_frame_padding=4))
        group = matched_files([dict(path='beauty.000000001.exr',size=0),dict(path='beauty.900000001.exr',size=0)])[0][0]
        self.assertEqual(group.get_metadata()['frameranges'],['1','900000001'])

    def test_native_groups_plans_versions_revision_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            self.store = Store(Path(directory) / 'data')
            self.api, ticket = prepare(self.store)
            self.api.protocol = 'json'
            self.auth = dict(ticket=ticket, project='one')
            self.values = dict(search_key='cg/shot?project=one&code=SH001', process='publish', context='publish', create_icon=False,
                               source_files=[dict(path='render/beauty.0001.png', size=5), dict(path='render/beauty.0003.png', size=6)])
            matched = self.call(action='match')['groups']
            self.assertEqual([(row['matchingType'], row['indices']) for row in matched], [('sequence', [0, 1])])
            self.assertEqual(matched[0]['metadata']['frameranges'], ['1', '3'])
            before = self.query('sthpw/snapshot', [('context', 'publish')])
            plan = self.call(action='plan')['plan']
            self.assertEqual(plan['version'], 1)
            self.assertEqual(self.call(action='plan',version=0)['plan']['version'],1)
            examples = self.call(action='templates',templates=['$FILENAME.$FRAME.$EXT','$FILENAME.$BOGUS'],example='beauty.0001.png')['templates']
            self.assertEqual(examples[0]['matched'],'sequence')
            self.assertEqual(examples[1]['validationError'],'Invalid matching template')
            self.assertEqual(self.call(action='plan', reserved_versions=[1, 2])['plan']['version'], 3)
            self.assertEqual(self.query('sthpw/snapshot', [('context', 'publish')]), before)
            self.upload()
            first = self.call(files=['frame1.png', 'frame3.png'])['snapshot']
            self.assertEqual(first['version'], 1)
            for path in plan['files'][0]['versioned']:
                self.assertTrue(Path(path).is_file(), path)
            files = self.query('sthpw/file', [('snapshot_code', first['code'])])
            self.assertEqual(len(files), 1)
            self.assertIn('frameranges', files[0]['metadata'])
            self.upload()
            second = self.call(files=['frame1.png', 'frame3.png'])['snapshot']
            self.assertEqual(second['version'], 2)
            self.assertTrue(all(Path(path).is_file() for path in plan['files'][0]['versioned']))
            self.assertEqual([Path(path).read_bytes() for path in plan['files'][0]['versionless']],[b'first',b'third'])
            self.upload()
            self.api.dispatch('upload_file',(self.auth,'frame1.png',Binary(b'failed first')))
            self.api.dispatch('upload_file',(self.auth,'frame3.png',Binary(b'failed third')))
            original = FileAppendCheckin.execute
            def fail(checkin):
                original(checkin)
                raise ValueError('late rollback')
            with patch.object(FileAppendCheckin, 'execute', fail), self.assertRaisesRegex(ValueError, 'late rollback'):
                self.call(files=['frame1.png', 'frame3.png'], is_revision=True, version=2)
            self.assertEqual(len(self.query('sthpw/snapshot', [('context', 'publish'), ('version', '>=', 1)])), 2)
            second_plan = self.call(action='plan',is_revision=True,version=2)['plan']
            self.assertEqual([Path(path).read_bytes() for path in second_plan['files'][0]['versioned']],[b'first',b'third'])
            self.assertEqual([Path(path).read_bytes() for path in second_plan['files'][0]['versionless']],[b'first',b'third'])
            self.upload()
            result = self.call(files=['frame1.png', 'frame3.png'], only_versionless=True)['snapshot']
            self.assertEqual(result['version'], -1)
            self.assertEqual([Path(path).read_bytes() for path in plan['files'][0]['versionless']],[b'first',b'third'])
            self.assertEqual(len(self.query('sthpw/snapshot', [('context', 'publish'), ('version', '>=', 1)])), 2)
            for changes in (dict(source_files=[dict(path='../secret', size=1)]), dict(repository_alias='plugins'), dict(explicit_filename='../bad'), dict(templates=['$FILENAME.$FRAME.$FRAME.$EXT']),dict(version=False)):
                with self.assertRaises((UserException,ValueError,CheckinException)):
                    self.call(action='plan', **changes)
            # Whole-group repository deletion and durable replay keep every member.
            from pyasm.search.search import RequestContext,request_context
            from pyasm.command import Command
            from pyasm.biz import Snapshot
            from tactic.ui.tools import DeleteCmd
            with request_context(RequestContext(self.store,'admin','one')):
                self.api.auth.bind_security('admin',self.auth['ticket'])
                command = DeleteCmd(sobject=Snapshot.get_by_code(first['code']),auto_discover=True)
                command.get_transaction().set_sync(False)
                Command.execute_cmd(command)
            self.assertFalse(any(Path(path).exists() for path in plan['files'][0]['versioned']))
            self.api.dispatch('undo',(self.auth,))
            self.assertEqual([Path(path).read_bytes() for path in plan['files'][0]['versioned']],[b'first',b'third'])
            self.api.dispatch('redo',(self.auth,))
            self.assertFalse(any(Path(path).exists() for path in plan['files'][0]['versioned']))
            # A writer can check in its visible owner; unrelated commands and revocation stay denied.
            from test_project_writes import install_writer,PASSWORD,set_rules
            self.api.dispatch('execute_cmd',(dict(self.auth,project='admin'),'tactic.command.CreateProjectCmd',dict(project_code='queue_access',project_title='Queue access',project_stype=['asset'])))
            parent = self.api.dispatch('insert',(dict(self.auth,project='queue_access'),'queue_access/asset',dict(code='PRIVATE',name='Private queue owner')))
            install_writer(self.store)
            rules = '<rules><rule group="project" code="queue_access" access="allow"/><rule group="search_type" code="queue_access/asset" project="queue_access" access="allow"/><rule group="search_type" code="sthpw/snapshot" access="allow"/><rule group="search_type" code="sthpw/file" access="allow"/></rules>'
            set_rules(self.store,rules)
            self.auth = dict(ticket=self.api.get_ticket('project_writer',PASSWORD),project='queue_access')
            self.values['search_key'] = parent['__search_key__']
            self.call(action='plan')
            self.upload(); snapshot = self.call(files=['frame1.png','frame3.png'])['snapshot']
            self.assertEqual(snapshot['version'],1)
            self.upload(); self.assertEqual(self.call(files=['frame1.png','frame3.png'])['snapshot']['version'],2)
            writer_plan = self.call(action='plan')['plan']
            collision = Path(writer_plan['files'][0]['versioned'][0]); collision.parent.mkdir(parents=True,exist_ok=True); collision.write_bytes(b'unregistered file')
            self.upload()
            with patch.object(FileAppendCheckin, 'execute', side_effect=ValueError('overwrite rollback')):
                with self.assertRaisesRegex(ValueError, 'overwrite rollback'):
                    self.call(files=['frame1.png','frame3.png'])
            self.assertEqual(collision.read_bytes(),b'unregistered file')
            self.assertEqual(self.call(files=['frame1.png','frame3.png'])['snapshot']['version'], 3)
            self.assertEqual(collision.read_bytes(),b'first')
            from tactic.command.browser_checkin_cmd import _check_existing_file
            from pyasm.common import Environment
            with request_context(RequestContext(self.store,'project_writer','queue_access')):
                self.api.auth.bind_security('project_writer',self.auth['ticket'])
                with self.assertRaisesRegex(UserException,'already exists'):
                    _check_existing_file(collision, Path(Environment.get_asset_dir()).resolve(), set())
            self.assertEqual(collision.read_bytes(),b'first')
            for kind in ('sthpw/snapshot','sthpw/file'):
                set_rules(self.store,rules.replace('code="%s" access="allow"' % kind,'code="%s" access="deny"' % kind))
                with self.assertRaises(SecurityException):
                    self.call(files=['frame1.png','frame3.png'])
                set_rules(self.store,rules)
            # Optional hard links cover every latest member and rollback/replay keeps numbered files.
            from pyasm.common import Config
            original_setting = Config.get_value
            writer_plan = self.call(action='plan')['plan']
            with patch.object(Config,'get_value',side_effect=lambda section,key,*args,**kwargs: 'hardlink' if (section,key) == ('checkin','versionless_mode') else original_setting(section,key,*args,**kwargs)):
                self.upload(); self.call(files=['frame1.png','frame3.png'])
            for original,latest in zip(writer_plan['files'][0]['versioned'],writer_plan['files'][0]['versionless']):
                self.assertTrue(os.path.samefile(original,latest))
            # A supplied operation preview uses native web/icon generation.
            import io
            from PIL import Image
            image = io.BytesIO(); Image.new('RGB',(8,8),(20,80,120)).save(image,format='PNG')
            self.api.dispatch('upload_file',(self.auth,'image.png',Binary(image.getvalue())))
            self.api.dispatch('upload_file',(self.auth,'note.txt',Binary(b'document')))
            preview = self.call(context='preview/test',source_files=[dict(path='note.txt',size=8),dict(path='preview/thumbnail.png',size=len(image.getvalue()),file_type='preview')],files=['note.txt','image.png'],create_icon=True)['snapshot']
            rows = self.query('sthpw/file',[('snapshot_code',preview['code'])])
            self.assertEqual({row['type'] for row in rows},{'main','preview','web','icon'})
            with self.assertRaises(SecurityException):
                self.api.dispatch('execute_cmd',(self.auth,'tactic.core.schema_commands.SearchTypeCreatorCmd',dict(search_type_name='one/not_allowed')))
            set_rules(self.store,rules.replace('code="queue_access/asset" project="queue_access" access="allow"','code="queue_access/asset" project="queue_access" access="deny"'))
            with self.assertRaises((SecurityException,LookupError)):
                self.call(files=['frame1.png','frame3.png'])

    def call(self, **changes):
        return self.api.dispatch('execute_cmd', (self.auth, 'tactic.command.browser_checkin_cmd.BrowserCheckinCmd', dict(self.values, **changes)))['info']

    def query(self, kind, filters):
        return self.api.dispatch('query', (self.auth, kind), dict(filters=filters))

    def upload(self):
        self.api.dispatch('upload_file', (self.auth, 'frame1.png', Binary(b'first')))
        self.api.dispatch('upload_file', (self.auth, 'frame3.png', Binary(b'third')))
