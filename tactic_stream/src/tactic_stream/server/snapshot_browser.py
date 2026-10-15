"""Handler SnapshotStateMixin/SnapshotDetailsMixin projection on native TACTIC records."""
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, quote

from pyasm.biz import File
from pyasm.search import Search
from pyasm.widget import ThumbWdg
from .table_cells import safe_link
from .file_presentation import metadata_members, metadata_display


def check_owner(owner):
    from .navigation_links import navigation_link_request
    navigation_link_request({'link':'skey://' + owner.get_search_key()}, preview=True)


def member_rows(file, row, offset=0, limit=50):
    names = metadata_members(file.get_json_value('metadata', default={}), offset, limit + 1)
    output = []
    for name in names[:limit]:
        path = Path(row['path']) / name
        address = urlsplit(row['href'])
        href = urlunsplit(address._replace(path=address.path.rsplit('/', 1)[0] + '/' + quote(name))) if row['href'] else ''
        output.append(dict(row, title=name, filename=name, fullPath=path.as_posix(), href=href, depth=3, size='', exists=path.exists()))
    if len(names) > limit:
        output.append(dict(row, rowType='more', title='Load more group files', depth=3, memberOffset=offset+limit))
    return output


def read_snapshot_members(file, offset=0, limit=50):
    from pyasm.biz import Snapshot
    snapshot = Snapshot.get_by_code(file.get_value('snapshot_code'))
    if snapshot is None or snapshot.get_sobject() is None:
        raise LookupError('Snapshot owner is no longer available')
    check_owner(snapshot.get_sobject())
    path = Path(file.get_lib_path())
    row = dict(rowType='file', token=file.get_code(), fileType=file.get_type(), path=path.parent.as_posix(),
               href=safe_link(file.get_web_path()), repository=snapshot.get_value('repo'), baseType=file.get_value('base_type'),
               previewType=file.get_type() in ('icon','web','playblast'), snapshotKey=snapshot.get_search_key(), record=dict(file.get_sobject_dict(),__search_key__=file.get_search_key()))
    return dict(rows=member_rows(file,row,offset,limit))


def preview_url(file):
    url = urlsplit(file['href'])
    try:
        stamp = Path(file['fullPath']).stat().st_mtime_ns
    except OSError:
        return file['href']
    query = [(name,value) for name,value in parse_qsl(url.query) if name != 'file_version']
    return urlunsplit(url._replace(query=urlencode([*query,('file_version',str(stamp))])))


def read_snapshot_browser(selected, process='', offset=0, limit=50):
    if not isinstance(process, str) or len(process) > 256:
        raise ValueError('Invalid process')
    snapshot = selected if selected.get_base_search_type() == 'sthpw/snapshot' else None
    if selected.get_base_search_type() == 'sthpw/file':
        from pyasm.biz import Snapshot
        snapshot = Snapshot.get_by_code(selected.get_value('snapshot_code'))
        if snapshot is None:
            raise LookupError('Snapshot is no longer available')
    owner = snapshot.get_sobject() if snapshot else selected
    if owner is None:
        raise LookupError('Snapshot owner is no longer available')
    check_owner(owner)
    if owner.get_base_search_type() == 'sthpw/task':
        process = process or owner.get_value('process')
        owner = owner.get_parent()
        if owner is None:
            raise LookupError('Task owner is no longer available')
        check_owner(owner)

    def query(versionless=None):
        search = Search('sthpw/snapshot')
        search.add_parent_filter(owner)
        if snapshot:
            search.add_filter('context', snapshot.get_value('context'))
            if snapshot.get_value('version') >= 0:
                search.add_filter('code', snapshot.get_code())
        elif process:
            search.add_op('begin')
            search.add_filter('context', process)
            search.add_filter('context', process + '/%', op='like')
            search.add_op('or')
        if versionless is not None:
            search.add_filter('version', 0, op='<' if versionless else '>=')
        search.add_order_by('context asc')
        search.add_order_by('version desc')
        search.add_order_by('id desc')
        return search

    # Native default process preference: publish, then icon, then the first context.
    if not snapshot and not process:
        for candidate in ('publish', 'icon', ''):
            process = candidate
            search = query()
            search.set_limit(1)
            first = search.get_sobject()
            if first:
                process = (first.get_value('context') or '').split('/')[0]
                break
    negative_count = query(True).get_count()
    snapshots = []
    if offset < negative_count:
        search = query(True)
        search.set_offset(offset)
        search.set_limit(limit + 1)
        snapshots = search.get_sobjects()
    if len(snapshots) <= limit:
        search = query(False)
        search.set_offset(max(0, offset - negative_count))
        search.set_limit(limit + 1 - len(snapshots))
        snapshots.extend(search.get_sobjects())
    has_next = len(snapshots) > limit
    snapshots = snapshots[:limit]
    grouped = defaultdict(list)
    for file in File.get_by_snapshots(snapshots):
        grouped[file.get_value('snapshot_code')].append(file)
    rows, previews, records = [], [], []
    seen_previews = set()
    for snapshot in snapshots:
        record = snapshot.get_sobject_dict()
        key = record['__search_key__'] = snapshot.get_search_key()
        records.append(record)
        rows.append(dict(rowType='snapshot', token='', title='Snapshot (%s), Version: %s' % (snapshot.get_id(), snapshot.get_value('version')),
                         depth=0, previewType=False, snapshotKey=key))
        files = grouped[snapshot.get_code()]
        descriptors = []
        ThumbWdg.get_file_info(snapshot.get_xml_value('snapshot'), {file.get_code():file for file in files}, snapshot, snapshot, files=descriptors)
        urls = {(item['type'],item['filename']):item['href'] for item in descriptors}
        types = defaultdict(list)
        for file in files:
            path = Path(file.get_lib_path())
            data = file.get_sobject_dict()
            data['__search_key__'] = file.get_search_key()
            filename = file.get_full_file_name()
            kind = file.get_type()
            row = dict(rowType='file', token=file.get_code(), title=filename, filename=filename,
                       fileType=kind, size=file.get_value('st_size', no_exception=True), path=path.parent.as_posix(), fullPath=path.as_posix(),
                       href=safe_link(urls.get((kind,filename), '')), repository=record.get('repo') or '',
                       baseType=file.get_value('base_type', no_exception=True) or '', depth=2, exists=path.exists(),
                       previewType=kind in ('icon', 'playblast', 'web'), snapshotKey=key, record=data)
            meta = metadata_display(file.get_json_value('metadata', default={}))
            if meta:
                row['title'] = meta['title']
            types[kind].append(row)
            types[kind].extend(member_rows(file,row))
        for kind, items in types.items():
            rows.append(dict(rowType='type', token='', title=kind, depth=1, previewType=kind in ('icon', 'playblast', 'web'), snapshotKey=key))
            rows.extend(items)
        # Prefer a web derivative, keeping the original file as the action target.
        web = types.get('web', [])
        candidates = [row for items in types.values() for row in items if row['fileType'] not in ('icon', 'web') and
                      (row['fileType'] in ('image','playblast') or Path(row['filename']).suffix.lower() in ('.png','.jpg','.jpeg','.tif','.tiff'))]
        if not candidates:
            candidates = web
        for row in candidates:
            if row['token'] in seen_previews or not row['href']:
                continue
            seen_previews.add(row['token'])
            derivative = web[0] if web else row
            previews.append(dict(file=row, url=preview_url(derivative) or preview_url(row), qualityUrl=preview_url(row), title=row['filename']))
    return dict(owner=owner.get_sobject_dict(), process=process, snapshots=records, rows=rows, previews=previews, has_next=has_next)
