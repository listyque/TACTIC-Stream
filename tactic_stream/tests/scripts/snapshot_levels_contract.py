"""Same snapshot/check-in calls in original TACTIC and Stream."""
import json
from pathlib import Path
from unittest.mock import patch
from pyasm.biz import Project, Snapshot, File
from pyasm.command import Command
from pyasm.common import Container, Environment, Xml, Config
from pyasm.web.api_xmlrpc import ApiXMLRPC
from pyasm.search import Search, SearchType
from pyasm.security import Security, Ticket


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        if not Environment.get_ticket():
            Environment.get_security()._ticket = Ticket.create('snapshot_levels_fixture', 'admin')
        parent = Project.get()
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = dict(project=Project.get_project_code(), language='python', ticket=Environment.get_ticket())
        if self.aliases:
            return level_aliases(api, ticket, Search.get_by_code('contract/entity', 'A'))
        naming = SearchType.create('config/naming')
        for key, value in dict(search_type='sthpw/project', snapshot_type='file',
            context='level_api', checkin_type='strict',
            file_naming='{basefile}.{ext}',
            dir_naming='{project.code}/levels/{snapshot.level_id}/{context}/{version}').items():
            naming.set_value(key, value, temp=True)
        Container.put('Naming:namings', [naming])
        Container.put('Naming:cache:admin', None)
        root = Environment.get_asset_dir().replace('\\', '/')
        def relative(path):
            return path.replace('\\', '/').replace(root, 'ASSETS')
        rows = []
        snapshots = []
        for code in ('admin', 'sthpw'):
            level = Search.get_by_code('sthpw/project', code)
            source = Path(Environment.get_upload_dir()) / (code + '.txt')
            source.write_text('payload ' + code, encoding='utf-8')
            row = api.simple_checkin(ticket, parent.get_search_key(), 'level_api', str(source),
                'file', 'Level file', False, 'main', True, level.get_search_key(),
                dict(label=code, nested=dict(ok=True)), None, False, {}, False, False,
                'pyasm.checkin.FileCheckin', None, 'strict', None, None, None)
            fetched = api.get_snapshot(ticket, parent.get_search_key(), 'level_api', 1,
                None, level.get_search_key(), False, True, False, True)
            assert fetched, (row, level.get_search_key(), level.get_search_type(), parent.get_search_type())
            xml = Xml(fetched['__full_snapshot_xml__'])
            paths = api.get_paths(ticket, parent.get_search_key(), 'level_api', 1,
                'main', level.get_search_key(), True, False, None, ['lib'])
            assert Path(paths['lib_path']).read_text(encoding='utf-8') == 'payload ' + code
            assert Snapshot.get_by_path(paths['lib_path']).get_code() == row['code']
            assert File.get_by_path(paths['lib_path']).get_file_name() == fetched['__files__'][0]['file_name']
            checkout = api.checkout(ticket, parent.get_search_key(), 'level_api', 1,
                                    'main', level.get_search_key())
            assert checkout['client_lib_paths'] == [paths['lib_path']]
            metadata = fetched['metadata']
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            rows.append([fetched['version'], metadata, xml.get_value('snapshot/@version'),
                xml.get_values('snapshot/file/@name'), relative(paths['lib_path'])])
            snapshots.append(Snapshot.get_by_code(row['code']))
        selected = api.query_snapshots(ticket, [['context', 'level_api']], None, [], False,
                                      None, None, False, False, True)
        assert len(selected) == 2 and all('__full_snapshot_xml__' in row for row in selected)
        contexts = Snapshot.get_contexts(parent.get_search_type(), parent.get_code())
        virtual = api.get_virtual_snapshot_path(ticket, parent.get_search_key(), 'level_api',
            'file', parent.get_search_key(), 'main', 'virtual.txt', False, None)
        assert not Path(virtual).exists()
        ref_errors = []
        for unused in range(2):
            try:
                snapshots[0].add_ref_by_snapshot(snapshots[1], tag='level')
            except Exception as error:
                ref_errors.append(type(error).__name__)
        ref = snapshots[0].get_xml_value('snapshot').get_node('snapshot/ref')
        assert Xml.get_attribute(ref, 'level_id') == str(snapshots[1].get_value('level_id'))
        snapshots[0].add_metadata(dict(extra=0))
        snapshots[0].commit()
        assert snapshots[0].get_metadata_dict()['label'] == 'admin'
        assert snapshots[0].get_metadata_dict()['extra'] == 0
        records = []
        for code in ('META_API_ONE', 'META_API_TWO'):
            records.append(dict(code=code, snapshot='<snapshot/>', search_type=parent.get_search_type(),
                search_id=parent.get_id(), search_code=parent.get_code(), project_code='admin',
                login='admin', context='metadata_api', process='metadata_api', version=1, is_current=False, is_latest=False))
        inserted = api.insert(ticket, 'sthpw/snapshot', records[0], dict(first=1), None, {}, False, False)
        batch = api.insert_multiple(ticket, 'sthpw/snapshot', [records[1]], [dict(first=2)], None, False, False)
        changed = api.update(ticket, [inserted['__search_key__'], batch[0]['__search_key__']],
            [dict(metadata=dict(zero=0)), {}], [dict(slot=1), dict(slot=2)], None, {}, False, False)
        upsert = api.insert_update(ticket, inserted['__search_key__'], {}, dict(upsert=True), None, {}, False, False)
        def metadata(row):
            value = row['metadata']
            return json.loads(value) if isinstance(value, str) else value
        api_metadata = [metadata(row) for row in changed] + [metadata(upsert)]
        note = SearchType.create('sthpw/note')
        for key, value in dict(code='LEVEL_CHILD', search_type=parent.get_search_type(),
            search_id=parent.get_id(), search_code=parent.get_code(), note='Child level',
            project_code='admin').items():
            note.set_value(key, value)
        note.commit()
        inherited = Snapshot.get_snapshot(parent.get_search_type(), parent.get_code(), 'level_api',
            level_type=note.get_search_type(), level_id=note.get_id())
        # Original hierarchy loop skips the direct parent. Keep this difference visible.
        hierarchy = inherited.get_version() if inherited else None
        for mode in ('latest', 'current'):
            alias = Snapshot.get_versionless(parent.get_search_type(), parent.get_code(),
                'alias_api', mode=mode)
            assert alias.get_version() == (-1 if mode == 'latest' else 0)
        aliases = [api.get_snapshot(ticket, parent.get_search_key(), 'alias_api', version,
                    None, None, False, False, False, False, False, True)['version'] for version in (-1, 0)]
        # Source mistakes the string '-1' for CURRENT and filters context=None literally.
        alias_fixes = [api.get_snapshot(ticket, parent.get_search_key(), 'alias_api', '-1',
                                       None, None, False, False, False, False, False, True)['version'],
                       bool(api.get_snapshot(ticket, parent.get_search_key(), 'publish', -1,
                                             None, None, False, False, False, False, False, True, 'alias_api'))]
        assert api.get_paths(ticket, parent.get_search_key(), 'alias_api', -1,
                             '*', None, False, True)['lib_paths'] == []
        if self.fail:
            raise ValueError('level API rollback')
        return dict(rows=rows, contexts=contexts, virtual=relative(virtual),
                    aliases=aliases, hierarchy=hierarchy, alias_fixes=alias_fixes,
                    ref_errors=ref_errors, api_metadata=api_metadata)


def level_aliases(api, ticket, parent):
    for mode in ('versioned', 'latest', 'current'):
        values = dict(search_type='contract/entity', snapshot_type='file', checkin_type='strict', context='level_alias_probe',
            file_naming='{basefile}.{ext}',
            dir_naming='{project.code}/level_alias_probe/{snapshot.level_id}/' + ('{version}' if mode == 'versioned' else mode))
        if mode != 'versioned':
            values[mode + '_versionless'] = True
        api.insert(ticket, 'config/naming', values)
    Container.put('Naming:namings', None)
    for suffix in ('', ':latest', ':current'):
        Container.put('Naming:cache:one' + suffix, None)
    levels = [None, Search.get_by_code('contract/entity', 'B'), Search.get_by_code('contract/entity', 'D')]
    for index, level in enumerate(levels):
        source = Path(Environment.get_upload_dir()) / 'level-alias.txt'
        source.write_text('level ' + str(index), encoding='utf-8')
        api.simple_checkin(ticket, parent.get_search_key(), 'level_alias_probe', str(source),
            level_key=level.get_search_key() if level else None, create_icon=False)
    rows = []
    codes = []
    for level in levels:
        for version in (-1, 0):
            key = level.get_search_key() if level else None
            row = api.get_snapshot(ticket, parent.get_search_key(), 'level_alias_probe',
                version=version, level_key=key, versionless=True)
            paths = api.get_paths(ticket, parent.get_search_key(), 'level_alias_probe',
                version=version, level_key=key, versionless=True, path_types=['lib'])
            codes.append(row['code'])
            rows.append([row['version'], bool(row.get('level_type')), Path(paths['lib_paths'][0]).read_text(encoding='utf-8')])
    return dict(rows=rows, alias_count=len(set(codes)))


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    security = Environment.get_security()
    old_ticket = security._ticket
    security._ticket = Search('sthpw/ticket').get_sobject()
    try:
        command = Run()
        command.fail = case.get('fail', False)
        command.aliases = case.get('level_aliases', False)
        original_config = Config.get_dict_value
        def config(section, key):
            if section == 'checkin' and key.endswith('_sandbox_dir'):
                return {'default': str(Path(Environment.get_tmp_dir()) / 'levels_sandbox')}
            return original_config(section, key)
        with patch.object(Config, 'get_dict_value', config):
            return Command.execute_cmd(command)
    finally:
        security._ticket = old_ticket
        Environment.set_security(previous)
