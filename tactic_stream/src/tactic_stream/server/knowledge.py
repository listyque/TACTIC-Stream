"""Authenticated web transport for the original Handler Knowledge Base procedure."""
import json
import hashlib
import uuid
from pathlib import Path

from pyasm.biz import Project, File, IconCreator
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchKey, SearchType, FileUndo
from .knowledge_query import knowledge_request as native_request
from .navigation_links import check_project, check_type
from .table_cells import safe_link

FIELDS = {'identity', 'document', 'organization', 'expected_revision', 'query', 'attachment_key', 'history_revision', 'related_types'}
OPERATIONS = {'initialize', 'list', 'load', 'save', 'save_draft', 'reserve', 'organize', 'history', 'history_revision', 'attachments', 'delete_attachment', 'link_index', 'upload', 'deletion', 'delete'}
WRITES = {'initialize', 'save', 'save_draft', 'reserve', 'organize', 'delete_attachment', 'upload', 'delete'}


def attachments(result):
    records = []
    for record in result.get('attachmentSnapshots', []):
        snapshot = SearchKey.get_by_search_key(record['__search_key__'].removeprefix('skey://'))
        files = snapshot.get_all_file_objects()
        web = next((file for file in files if file.get_type() == 'web'), None)
        for file in files:
            if file.get_type() in ('web', 'icon'):
                continue
            metadata = file.get_json_value('metadata', default={})
            name = metadata.get('filename') or file.get_file_name()
            records.append(dict(token=file.get_code(), snapshotKey=record['__search_key__'], title=name,
                extension=Path(name).suffix.lstrip('.').upper(), size=file.get_value('st_size'),
                webUrl=safe_link(file.get_web_path()), previewUrl=safe_link((web or file).get_web_path()),
                isImage=Path(name).suffix.lower().lstrip('.') in file.IMAGE_EXT))
    result['attachments'] = records
    return result


def upload(arguments, uploads):
    if not uploads or len(uploads) != 1:
        raise ValueError('One attachment file is required')
    loaded = json.loads(native_request('attachments', Project.get_project_code(), identity=arguments.get('identity', '')))
    if not loaded.get('identity') or loaded.get('document', {}).get('kind') != 'article':
        raise ValueError('Select an existing Knowledge Base article')
    for kind in ('sthpw/snapshot', 'sthpw/file'):
        check_type(kind, Project.get_project_code())
    from .api import upload_file_name
    from pyasm.checkin import FileCheckin
    article = SearchKey.get_by_search_key(loaded['searchKey'].removeprefix('skey://'))
    filename, content = uploads[0]
    filename = upload_file_name(filename)
    token = uuid.uuid4().hex
    directory = Path(Environment.get_upload_dir()) / ('knowledge_' + token)
    FileUndo.mkdir(str(directory))
    path = directory / filename
    FileUndo.create(str(path), io_action=False)
    path.write_bytes(content)
    image = path.suffix.lower().lstrip('.') in File.IMAGE_EXT
    paths, types = [str(path)], ['preview' if image else 'file']
    if image:
        creator = IconCreator(str(path)); creator.execute()
        for kind, value in (('web', creator.get_web_path()), ('icon', creator.get_icon_path())):
            if value:
                paths.append(value); types.append(kind)
    command = FileCheckin(article, paths, file_types=types, context='attachment/knowledge/' + token,
        description='Knowledge Base attachment', mode='create', source_paths=paths,
        keep_file_name=False, do_update_versionless=False, process='attachment',
        file_naming='{sobject.code}_' + token + '_{file_type}.{ext}')
    command.execute()
    snapshot = command.get_snapshot()
    for file in snapshot.get_all_file_objects():
        if file.get_type() not in ('web', 'icon'):
            file.add_metadata({'filename': filename}, replace=False); file.commit(triggers=False)
    if not any(directory.iterdir()):
        FileUndo.rmdir(str(directory))
    return json.loads(native_request('attachments', Project.get_project_code(), identity=arguments['identity']))


def knowledge_request(action, payload, uploads=None):
    if action not in OPERATIONS or set(payload) - {'ticket', 'project'} - FIELDS:
        raise ValueError('Unknown Knowledge Base operation or argument')
    project = Project.get_project_code()
    check_project(project)
    kind = project + '/th_knowledge_article'
    if SearchType.get(kind, no_exception=True):
        check_type(kind, project)
    arguments = {key: value for key, value in payload.items() if key in FIELDS}
    for key in FIELDS - {'document', 'organization', 'related_types'}:
        value = arguments.get(key, '')
        if not isinstance(value, str) or len(value) > (2048 if key == 'query' else 4096) or '\x00' in value:
            raise ValueError('Invalid Knowledge Base argument: ' + key)
    if 'document' in arguments and not isinstance(arguments['document'], dict):
        raise ValueError('Invalid Knowledge Base document')
    if 'organization' in arguments and not isinstance(arguments['organization'], list):
        raise ValueError('Invalid Knowledge Base organization')
    def execute():
        if action in WRITES and action != 'initialize':
            kind = project + '/th_knowledge_article'
            if SearchType.get(kind, no_exception=True):
                sql = Search(kind).get_sql()
                sql.get_database_impl().lock_collection_table(sql, 'th_knowledge_article')
        try:
            if action in ('deletion', 'delete'):
                from .object_operations import deletion_groups
                from tactic.ui.tools import DeleteCmd
                loaded = json.loads(native_request('load', project, identity=arguments.get('identity', '')))
                if not loaded.get('canEdit'):
                    raise SecurityException('Supervisor access is required to edit articles')
                if not loaded.get('identity'):
                    raise ValueError('Select an existing Knowledge Base entry')
                if any(row['parentCode'] == loaded['identity'] for row in loaded['catalog']):
                    raise ValueError('Move or delete child pages before deleting this section')
                obj = SearchKey.get_by_search_key(loaded['searchKey'].removeprefix('skey://'))
                groups = deletion_groups([obj])
                if action == 'deletion':
                    return dict(groups=groups)
                selected = arguments.get('related_types')
                if not isinstance(selected, list) or any(not isinstance(kind, str) or kind not in {group['search_type'] for group in groups} for kind in selected):
                    raise ValueError('Dependency selection changed. Reopen the deletion dialog.')
                if loaded['revision'] != arguments.get('expected_revision'):
                    raise ValueError('This article changed on the server. Reload it before deleting.')
                cmd = DeleteCmd(search_keys=[obj.get_search_key()], values=dict(related_types=[obj.get_base_search_type(), *selected]))
                Command.execute_cmd(cmd)
                return json.loads(native_request('list', project))
            if 'related_types' in arguments:
                raise ValueError('Dependency selection is only available for deletion')
            if action == 'organize':
                catalog = json.loads(native_request('list', project))['catalog']
                if arguments.get('expected_revision') != catalog_revision(catalog):
                    raise ValueError('The article organization changed on the server. Reload before saving order.')
            result = upload(arguments, uploads) if action == 'upload' else json.loads(native_request(action, project, **arguments))
            if 'catalog' in result:
                catalog = result['catalog'] if not arguments.get('query') else json.loads(native_request('list', project))['catalog']
                result['catalogRevision'] = catalog_revision(catalog)
            return attachments(result)
        except PermissionError as error:
            raise SecurityException(str(error)) from error
    if action not in WRITES:
        return execute()
    command = Command(); command.get_transaction().set_sync(False); command.execute = execute
    return Command.execute_cmd(command)


def catalog_revision(catalog):
    rows = sorted((row['identity'], row['parentCode'], row['sortOrder']) for row in catalog)
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode()).hexdigest()
