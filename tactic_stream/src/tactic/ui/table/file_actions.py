"""Snapshot append keeps the selected revision and uses native FileUndo/check-in."""
from pyasm.command import Command


def append_snapshot_files(search_key, action='prepare', expected_revision='',
                          filenames=None, file_type='attachment', keep_file_name=False,
                          upload_directory=''):
    """Self-contained procedure for Stream and an original TACTIC server."""
    import hashlib
    import json
    import os
    import re
    import uuid
    from pyasm.biz import Project, Snapshot
    from pyasm.checkin import FileAppendCheckin
    from pyasm.common import Environment
    from pyasm.search import Search, SearchKey

    if not Environment.get_security().is_admin():
        raise PermissionError('Administration requires administrator access')
    if action not in ('prepare', 'save'):
        raise ValueError('Invalid snapshot append action')
    if SearchKey.extract_base_search_type(search_key) != 'sthpw/snapshot':
        raise ValueError('Append files requires a snapshot')
    snapshot = Search.get_by_search_key(search_key)
    if snapshot is None:
        raise LookupError('Snapshot is no longer available')
    if snapshot.get_value('project_code') != Project.get_project_code():
        raise ValueError('Open the snapshot in its own project before attaching files')
    alias_version = int(snapshot.get_value('version'))
    if alias_version <= 0:
        if action != 'prepare':
            raise ValueError('Reload the concrete snapshot version before attaching files')
        parent = snapshot.get_sobject()
        if parent is None:
            raise LookupError('Snapshot owner is no longer available')
        snapshot = Snapshot.get_snapshot(parent.get_search_type(), parent.get_code() or parent.get_id(),
            context=snapshot.get_value('context'), version=alias_version, revision=-1,
            level_type=snapshot.get_value('level_type'), level_id=snapshot.get_value('level_id'),
            process=snapshot.get_value('process') or None, use_cache=False, level_parent_search=False)
        if snapshot is None or int(snapshot.get_value('version')) <= 0:
            raise LookupError('No concrete snapshot version is available')
    if action == 'save':
        sql = snapshot.get_sql()
        lock = getattr(sql.get_database_impl(), 'lock_collection_table', None)
        if lock:
            lock(sql, 'snapshot')
        elif sql.get_database_type() == 'PostgreSQL':
            sql.do_update('LOCK TABLE "snapshot" IN EXCLUSIVE MODE')
        else:
            raise ValueError('Snapshot revisions require a transactional database lock')
        snapshot = Search.get_by_search_key(snapshot.get_search_key())
        if snapshot is None:
            raise LookupError('Snapshot is no longer available')
        if snapshot.get_value('project_code') != Project.get_project_code():
            raise ValueError('Open the snapshot in its own project before attaching files')
    files = snapshot.get_all_file_objects()
    revision = hashlib.sha256(json.dumps([snapshot.get_data(), sorted(
        (item.get_data() for item in files), key=lambda item: str(item.get('code') or item.get('id')))],
        sort_keys=True, default=str).encode()).hexdigest()
    existing = [str(item.get_value('file_name') or '') for item in files]
    if action == 'prepare':
        parent = snapshot.get_sobject()
        if parent is None:
            raise LookupError('Snapshot owner is no longer available')
        return dict(searchKey=snapshot.get_search_key(), snapshotCode=snapshot.get_code(),
            version=snapshot.get_value('version'), expectedRevision=revision, existingNames=existing,
            uploadDirectory='append_' + uuid.uuid4().hex,
            ownerKey=parent.get_search_key(), ownerTitle=str(parent.get_display_value()),
            context=snapshot.get_value('context'), process=snapshot.get_value('process') or
            str(snapshot.get_value('context') or '').split('/')[0])
    if not expected_revision or revision != expected_revision:
        raise ValueError('Snapshot changed. Reload before attaching files.')
    if not isinstance(filenames, list) or not 1 <= len(filenames) <= 50:
        raise ValueError('Choose between one and 50 files')
    if not isinstance(file_type, str) or not file_type.strip() or len(file_type) > 128 or any(
            ord(character) < 32 for character in file_type):
        raise ValueError('Choose a valid file type')
    if type(keep_file_name) is not bool:
        raise ValueError('Invalid keep-file-name option')
    if not isinstance(upload_directory, str) or not re.fullmatch(r'append_[a-f0-9]{32}', upload_directory):
        raise ValueError('Reload the attachment session before uploading files')
    names, paths = set(), []
    upload_root = os.path.realpath(Environment.get_upload_dir())
    directory = os.path.realpath(os.path.join(upload_root, upload_directory))
    if os.path.normcase(os.path.commonpath([directory, upload_root])) != os.path.normcase(upload_root):
        raise ValueError('Uploaded files must remain in the ticket upload directory')
    for name in filenames:
        if not isinstance(name, str) or name in ('', '.', '..') or any(
                character in name for character in ('/', '\\', ':', '\x00')) or any(
                ord(character) < 32 for character in name):
            raise ValueError('Uploaded files must be named without directory paths')
        folded = name.casefold()
        if folded in names or folded in {value.casefold() for value in existing}:
            raise ValueError('Choose file names that are not already in the snapshot')
        names.add(folded)
        path = os.path.realpath(os.path.join(directory, name))
        if os.path.normcase(os.path.commonpath([path, directory])) != os.path.normcase(directory) or not os.path.isfile(path):
            raise ValueError('Uploaded file is unavailable: ' + name)
        paths.append(path)
    # All names, the complete revision and ticket-owned uploads are checked before a write.
    checkin = FileAppendCheckin(snapshot.get_code(), paths, [file_type.strip()] * len(paths),
        mode='create', keep_file_name=keep_file_name, source_paths=list(filenames))
    checkin.execute()
    return dict(state='saved', searchKey=checkin.get_snapshot().get_search_key())


class TableSnapshotAppendCmd(Command):
    def execute(self):
        self.info = append_snapshot_files(**self.kwargs)
        return self.info


def read_snapshot_files(search_key, file_code='', expected_revision=''):
    """Read a captured concrete snapshot using only original server methods."""
    import json
    import hashlib
    import os
    from pyasm.biz import FileGroup, FileRange, Project, Snapshot
    from pyasm.common import Environment
    from pyasm.search import Search, SearchKey

    if not Environment.get_security().is_admin():
        raise PermissionError('Administration requires administrator access')
    if SearchKey.extract_base_search_type(search_key) != 'sthpw/snapshot':
        raise ValueError('Check out requires a snapshot')
    snapshot = Search.get_by_search_key(search_key)
    if snapshot is None:
        raise LookupError('Snapshot is no longer available')
    if snapshot.get_value('project_code') != Project.get_project_code():
        raise ValueError('Open the snapshot in its own project before checking out files')
    if SearchKey.extract_base_search_type(snapshot.get_value('search_type') or '') in ('sthpw/message', 'sthpw/message_log'):
        raise ValueError('Download private message attachments from Messages')
    version = int(snapshot.get_value('version'))
    if version <= 0:
        parent = snapshot.get_sobject()
        if parent is None:
            raise LookupError('Snapshot owner is no longer available')
        snapshot = Snapshot.get_snapshot(parent.get_search_type(), parent.get_code() or parent.get_id(),
            context=snapshot.get_value('context'), version=version, revision=-1,
            level_type=snapshot.get_value('level_type'), level_id=snapshot.get_value('level_id'),
            process=snapshot.get_value('process') or None, use_cache=False, level_parent_search=False)
        if snapshot is None or int(snapshot.get_value('version')) <= 0:
            raise LookupError('No concrete snapshot version is available')
    if snapshot.get_value('project_code') != Project.get_project_code():
        raise ValueError('Open the snapshot in its own project before checking out files')
    if expected_revision and hashlib.sha256(json.dumps(snapshot.get_data(), sort_keys=True, default=str).encode()).hexdigest() != expected_revision:
        raise ValueError('Dependencies changed. Reload this snapshot.')
    files = snapshot.get_all_file_objects()
    if file_code:
        files = [file for file in files if file.get_code() == file_code]
        if len(files) != 1:
            raise LookupError('Dependency file is no longer available')
    rows = []
    for file in files:
        row = file.get_sobject_dict()
        meta = file.get_metadata_dict()
        file_range = str(file.get_value('file_range', no_exception=True) or '').strip()
        template = str(meta.get('new_template') or meta.get('template') or '').strip()
        group_type = str(meta.get('type') or '').strip()
        if file_range or (template and group_type not in ('', 'file', 'layer_file', 'no_ext')):
            if file_code:
                raise ValueError('Sequence and UDIM files require Snapshot Checkout')
            name = file.get_full_file_name()
            names = []
            if file_range:
                rng = FileRange.get(file_range)
                if rng.get_num_frames() > 5000:
                    raise ValueError('Sequence or UDIM group exceeds the checkout limit')
                names = FileGroup.expand_paths(name, rng)
            else:
                stem, suffix = os.path.splitext(name)
                base = str(meta.get('new_filename') or meta.get('filename') or stem)
                ext = str(meta.get('new_file_ext') or meta.get('ext') or suffix.lstrip('.'))
                layer = str(meta.get('layer') or '')
                pad = int(meta.get('new_padding') or meta.get('padding') or 4)
                render = lambda udim='', frame=None: (template
                    .replace('$FILENAME', base).replace('$LAYER', layer)
                    .replace('$UDIM', str(udim)).replace('$UV', str(udim))
                    .replace('$FRAME', '' if frame is None else str(frame).zfill(pad))
                    .replace('$EXT', ext))
                parse_span = lambda item: (int(item[0]), int(item[1])) if isinstance(item, (list, tuple)) else [int(part) for part in str(item).split('-')]
                if group_type in ('sequence', 'layer_sequence'):
                    for item in meta.get('frameranges') or []:
                        start, end = parse_span(item)
                        if end < start or len(names) + (end - start + 1) > 5000:
                            raise ValueError('Sequence or UDIM group exceeds the checkout limit')
                        names.extend(render(frame=frame) for frame in range(start, end + 1))
                elif group_type in ('udim', 'uv', 'layer_udim', 'layer_uv'):
                    for udim in meta.get('udims') or []:
                        if len(names) + 1 > 5000:
                            raise ValueError('Sequence or UDIM group exceeds the checkout limit')
                        names.append(render(udim=udim))
                elif group_type in ('udim_sequence', 'uv_sequence', 'layer_udim_sequence', 'layer_uv_sequence'):
                    for pair in meta.get('frameranges') or []:
                        udim, ranges = pair[0], pair[1]
                        for item in ranges or []:
                            start, end = parse_span(item)
                            if end < start or len(names) + (end - start + 1) > 5000:
                                raise ValueError('Sequence or UDIM group exceeds the checkout limit')
                            names.extend(render(udim=udim, frame=frame) for frame in range(start, end + 1))
            if not names or len(set(names)) != len(names):
                raise ValueError('Sequence or UDIM group has no valid member files')
            sizes = meta.get('files_sizes') or []
            row['__member_files__'] = [
                dict(file_name=member, st_size=int(sizes[idx] or 0) if idx < len(sizes) else 0)
                for idx, member in enumerate(names)
            ]
        rows.append(row)
    data = snapshot.get_sobject_dict()
    data['__files__'] = rows
    return json.loads(json.dumps(data, default=str))


class TableSnapshotFilesCmd(Command):
    def execute(self):
        from urllib.parse import quote, urlsplit, urlunsplit
        from pyasm.common import Xml
        from pyasm.search import Search
        from pyasm.widget import ThumbWdg
        from tactic_stream.server.api import ApiXMLRPC
        from tactic_stream.server.table_cells import safe_link

        data = read_snapshot_files(**self.kwargs)
        snapshot = Search.get_by_search_key(data['__search_key__'])
        by_code = {file['code']: file for file in data['__files__']}
        selected = set(by_code)
        source = snapshot.get_snapshot_xml()
        xml = Xml()
        xml.read_string('<snapshot>' + ''.join(
            source.to_string(node, pretty=False) for node in source.get_nodes('snapshot/file')
            if Xml.get_attribute(node, 'file_code') in selected) + '</snapshot>')
        objects = {file.get_code(): file for file in snapshot.get_all_file_objects() if file.get_code() in selected}
        files = []
        # The normal Thumb path must not expand unrelated sequences in this snapshot.
        ThumbWdg.get_file_info(xml, objects, snapshot, snapshot, files=files)
        for file in files:
            file['href'] = safe_link(file['href'])
            members = by_code.get(file['code'], {}).get('__member_files__')
            if members:
                web_dir = snapshot.get_web_dir(snapshot, file_object=objects[file['code']]).replace('\\', '/')
                url = urlsplit(web_dir)
                file['members'] = [
                    dict(
                        filename=member['file_name'],
                        size=int(member.get('st_size') or 0),
                        href=safe_link(urlunsplit((url.scheme, url.netloc, quote(url.path + '/' + member['file_name'], safe='/:'), url.query, url.fragment))),
                    )
                    for member in members
                ]
        self.info = dict(snapshot=ApiXMLRPC._record(snapshot), files=files)
        return self.info
