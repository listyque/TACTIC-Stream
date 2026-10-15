"""One unchanged repository/group API script for both actual kernels and vendors."""
import json
from pathlib import Path
from pyasm.biz import Project, Snapshot
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.web.api_xmlrpc import ApiXMLRPC
from pyasm.search import Search
from pyasm.security import Security, Ticket


def paths(value):
    if isinstance(value, dict):
        return {key: paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [paths(item) for item in value]
    value = str(value).replace('\\', '/')
    at = value.find('/admin/project/')
    return value[at+1:] if at != -1 else value


def record(row):
    return {key: row.get(key) for key in ('version', 'revision', 'context', 'snapshot_type', 'description')}


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        if not Environment.get_ticket():
            Environment.get_security()._ticket = Ticket.create('file_api_fixture', 'admin')
        parent = Project.get()
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = {'project': Project.get_project_code(), 'language': 'python'}
        directory = Path(Environment.get_upload_dir())
        results = []
        snapshots = []
        for version in (1, 2):
            for frame in (1, 2, 3):
                (directory / ('image.%04d.txt' % frame)).write_text('frame '+str(frame), encoding='utf-8')
            row = api.group_checkin(ticket, parent.get_search_key(), 'file_api', 'image.####.txt', '1-3', 'sequence', '', 'main', {'label': 'Frames', 'nested': {'count': 3}}, 'upload')
            assert row['version'] == str(version) and isinstance(row['id'], str)
            metadata = row['metadata']
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            assert metadata == {'label': 'Frames', 'nested': {'count': 3}}
            snapshots.append(row['code'])
            results.append(record(row))
        row = api.set_current_snapshot(ticket, snapshots[0])
        assert row['is_current']
        for frame in (1, 2, 3):
            (directory / ('extra.%04d.txt' % frame)).write_text('extra '+str(frame), encoding='utf-8')
        appended = api.add_group(ticket, row, 'extra.####.txt', 'extra', '1-3', False, 'upload')
        assert appended['code'] == row['code'] and appended['version'] == 1
        selected = api.query_snapshots(ticket, [['context', 'file_api'], ['version', '>', 0]], None, ['version'], False, None, None, False, True, False, True, True, True, True)
        query = []
        for item in selected:
            assert item['__parent__']['code'] == parent.get_code()
            query.append([record(item), sorted(file['type'] for file in item['__files__']), paths(item['__paths__']), paths(item['__paths_dict__']), paths(item['__web_paths_dict__'])])
        assert api.query_snapshots(ticket, [['context', 'missing_file_api']]) == []
        assert len(api.query_snapshots(ticket, [['context', 'file_api']], None, ['version'], False, None, None, True)) == 1
        row = snapshots[0]
        read_paths = []
        for mode in ('lib', 'client_repo', 'web', 'relative'):
            read_paths.append([paths(api.get_client_dir(ticket, row, 'main', mode)), paths(api.get_path_from_snapshot(ticket, row, 'main', mode)), paths(api.get_all_paths_from_snapshot(ticket, row, mode, True))])
        expanded = api.get_expanded_paths_from_snapshot(ticket, {'code': row}, 'main')
        assert len(expanded) == 3
        reads = api.get_paths(ticket, parent.get_search_key(), 'file_api', 1, 'main', None, False, False, None, ['client', 'lib', 'relative'])
        relative = Snapshot.get_by_code(snapshots[1]).get_relative_dir()
        found = api.get_snapshots_by_relative_dir(ticket, relative)
        first = Snapshot.get_by_code(row)
        second = Snapshot.get_by_code(snapshots[1])
        xml = first.get_snapshot_xml()
        node = xml.create_element('ref', node=xml.get_root_node())
        for key, value in {'snapshot_code': second.get_code(), 'search_type': parent.get_search_type(), 'search_code': parent.get_code(), 'context': 'file_api', 'version': 2, 'tag': 'main'}.items():
            xml.set_attribute(node, key, value)
        first.set_value('snapshot', xml.to_string())
        first.commit()
        direct = api.get_dependencies(ticket, row, 'explicit', 'main', True, True, False)
        all_refs = api.get_all_dependencies(ticket, row, 'explicit', 'ref', True, True, True)
        assert [item['code'] for item in direct] == [second.get_code()]
        assert len(all_refs[0]['__files__']) == 1
        bases = api.get_base_dirs(ticket)
        assert isinstance(bases, dict)
        if self.fail:
            raise ValueError('file API rollback')
        return {'groups': results, 'query': query, 'paths': read_paths, 'expanded': paths(expanded),
                'reads': paths(reads), 'refs': [[record(item), paths(item['__paths__']), paths(item['__paths_dict__'])] for item in direct],
                'all_refs': [[record(item), [file['type'] for file in item['__files__']]] for item in all_refs],
                'found_latest': any(item['code'] == snapshots[1] for item in found),
                'latest_flags': [[item['version'], bool(item['is_latest'])] for item in selected],
                'current_flags': [[item['version'], bool(item['is_current'])] for item in selected],
                'base_keys': sorted(key for key in bases if key in ('asset_base_dir', 'web_base_dir'))}


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
        return Command.execute_cmd(command)
    finally:
        security._ticket = old_ticket
        Environment.set_security(previous)
