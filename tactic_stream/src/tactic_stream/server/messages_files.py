"""Handler attachment targets, using native check-in, repository naming and FileUndo."""
import hashlib
import json
import mimetypes
import uuid
from pathlib import Path

from pyasm.biz import IconCreator, Project
from pyasm.checkin import FileCheckin
from pyasm.common import Container, Environment
from pyasm.common.errors import SecurityException
from pyasm.search import FileUndo, Search, SearchKey
from .messages import _conversation, _record, _require_access


def snapshot_record(snapshot):
    row = snapshot.get_data()
    row['__search_key__'] = SearchKey.get_by_sobject(snapshot, use_id=False)
    row['__files__'] = [file.get_data() for file in snapshot.get_all_file_objects()]
    return row


def upload_attachment(arguments, uploads):
    if not uploads or len(uploads) != 1:
        raise ValueError('One attachment file is required')
    filename, content = uploads[0]
    from .api import upload_file_name
    filename = upload_file_name(filename)
    token = uuid.UUID(arguments['token']).hex
    conversation = _conversation(arguments['message_code'])
    preview = arguments['purpose'] == 'preview'
    if arguments['purpose'] not in ('attachment', 'preview'):
        raise ValueError('Invalid attachment purpose')
    if preview:
        from . import messages_query
        catalog = json.loads(messages_query.query_chat_conversations())
        row = next(row for row in catalog['conversations'] if row['conversationId'] == conversation.get_code())
        if not row['canManage']:
            raise SecurityException('Only the chat owner or supervisor can change its preview')
    for kind in ('sthpw/snapshot', 'sthpw/file'):
        _require_access(kind, 'edit')
    digest = hashlib.sha256(content).hexdigest()
    context = ('icon/' if preview else 'attachment/chat/' + conversation.get_code() + '/') + token
    existing = Search('sthpw/snapshot')
    existing.add_sobject_filter(conversation)
    existing.add_filter('context', context)
    snapshot = existing.get_sobject()
    if snapshot:
        metadata = snapshot.get_json_value('metadata', default={}).get('chatAttachment', {})
        if metadata != {'token': token, 'name': filename, 'sha256': digest, 'login': Environment.get_user_name()}:
            raise ValueError('Attachment identity was already used for another file')
        return snapshot_record(snapshot)
    original_project = Project.get_project_code()
    directory = Path(Environment.get_upload_dir()) / ('chat_' + token)
    scope = {'message_code': conversation.get_code(), 'project': original_project,
             'paths': {str(directory.resolve()), str((Path(Environment.get_tmp_dir()) / 'undo').resolve())}}
    Container.put('Chat:attachment', scope)
    try:
        FileUndo.mkdir(str(directory))
        path = directory / filename
        if path.exists():
            raise ValueError('Attachment staging file already exists')
        FileUndo.create(str(path), io_action=False)
        path.write_bytes(content)
        file_type = 'preview' if path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tif', '.tiff') else 'file'
        if preview and file_type != 'preview':
            raise ValueError('A conversation preview must be an image')
        paths, types = [str(path)], [file_type]
        if file_type == 'preview':
            creator = IconCreator(str(path))
            creator.execute()
            for kind, value in (('web', creator.get_web_path()), ('icon', creator.get_icon_path())):
                if value:
                    paths.append(value); types.append(kind)
        checkin = FileCheckin(conversation, paths, file_types=types, context=context,
            description='Chat preview' if preview else 'Chat attachment', mode='create',
            source_paths=paths, keep_file_name=False, checkin_type='strict',
            do_update_versionless=False, process='icon' if preview else 'attachment')
        checkin.execute()
        snapshot = checkin.get_snapshot()
        snapshot.add_metadata({'chatAttachment': {'token': token, 'name': filename,
            'sha256': digest, 'login': Environment.get_user_name()}}, replace=False)
        snapshot.commit(triggers=False)
        if not any(directory.iterdir()):
            FileUndo.rmdir(str(directory))
        return snapshot_record(snapshot)
    finally:
        Project.set_project(original_project)


def attachment_file(arguments):
    from . import messages_query
    conversation = _conversation(arguments['message_code'])
    snapshot = _record(arguments['snapshot_code'], 'sthpw/snapshot')
    if not snapshot or snapshot.get_value('search_type') != 'sthpw/message':
        raise SecurityException('Attachment does not belong to this chat')
    metadata = snapshot.get_json_value('metadata', default={}).get('chatAttachment', {})
    connections = Search('sthpw/connection')
    connections.add_filter('src_search_type', 'sthpw/snapshot')
    connections.add_filter('src_search_id', snapshot.get_id())
    connections.add_filter('context', 'chat_attachment')
    own_draft = (snapshot.get_value('search_code') == conversation.get_code() and
                 metadata.get('login') == Environment.get_user_name() and connections.get_sobject() is None)
    authorized = json.loads(messages_query.authorize_chat_attachment(conversation.get_code(), snapshot.get_code()))['allowed']
    preview = snapshot.get_value('search_code') == conversation.get_code() and snapshot.get_value('process') == 'icon'
    if not authorized and not preview and not own_draft:
        raise SecurityException('Attachment is not linked to an available chat message')
    file = _record(arguments['file_code'], 'sthpw/file')
    if not file or file.get_value('snapshot_code') != snapshot.get_code():
        raise SecurityException('File does not belong to this attachment')
    path = Path(file.get_lib_path()).resolve()
    if not any(path.is_relative_to(Path(root).resolve()) for root in Environment.get_asset_dirs().values()):
        raise SecurityException('Attachment path is outside its repository')
    if not path.is_file():
        raise ValueError('Attachment file is missing from its repository')
    filename = metadata.get('name') if file.get_value('type') not in ('web', 'icon') else file.get_value('file_name')
    return {'path': str(path), 'filename': filename or path.name,
            'media_type': mimetypes.guess_type(str(path))[0] or 'application/octet-stream'}


def attachment_info(arguments):
    info = attachment_file(arguments)
    info['path'] = info['path'].replace('\\', '/')
    info['snapshot'] = snapshot_record(_record(arguments['snapshot_code'], 'sthpw/snapshot'))
    info['file'] = _record(arguments['file_code'], 'sthpw/file').get_data()
    return info
