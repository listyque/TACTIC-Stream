# Copyright (c) 2005-2010 Southpaw Technology. See LICENSE.TACTIC.
"""Original file ingest action for configured DropElementWdg rows."""
from pyasm.command import DatabaseAction


def ingest_drop_files(
    search_key,
    files=None,
    dirs=None,
    upload_directory=None,
    transfer_mode=None,
    checkin_mode=None,
    context=None,
    subcontext_mode=None,
    subcontext=None,
):
    """Self-contained procedure also executed against an original TACTIC server."""
    import os
    from pyasm.biz import Project
    from pyasm.checkin import FileCheckin
    from pyasm.common import Environment
    from pyasm.search import SearchKey

    if not search_key:
        raise ValueError('Select a target item')
    if SearchKey.extract_project(search_key) not in (None, '', Project.get_project_code()):
        raise ValueError('The configured table target belongs to another project')
    sobject = SearchKey.get_by_search_key(search_key)
    if not sobject or sobject.is_insert():
        raise ValueError('The configured table target is unavailable')

    base_dir = os.path.abspath(Environment.get_upload_dir())
    if upload_directory:
        if upload_directory in ('.', '..') or any(sep in str(upload_directory) for sep in ('/', '\\')):
            raise ValueError('Invalid staged upload path')
        base_dir = os.path.abspath(os.path.join(base_dir, str(upload_directory)))

    raw_items = [str(item) for item in (files or dirs or []) if str(item or '').strip()]
    if not raw_items:
        raise ValueError('Select at least one file')

    checkin_mode = str(checkin_mode or 'default').strip() or 'default'
    if checkin_mode not in ('default', 'file', 'file_group'):
        raise ValueError(f'Unsupported checkin mode: {checkin_mode}')
    subcontext_mode = str(subcontext_mode or '{none}').strip() or '{none}'
    if subcontext_mode not in ('{none}', '{leaf}', '{folder}', '{custom}'):
        raise ValueError(f'Unsupported subcontext mode: {subcontext_mode}')
    transfer_mode = str(transfer_mode or 'free_copy').strip() or 'free_copy'
    if transfer_mode not in ('upload', 'uploaded', 'free_copy', 'copy', 'free_move', 'move'):
        raise ValueError(f'Unsupported transfer mode: {transfer_mode}')
    transfer_mode = {'upload': 'uploaded', 'free_copy': 'copy', 'free_move': 'move'}.get(transfer_mode, transfer_mode)
    context = str(context or 'publish').strip('/') or 'publish'
    subcontext = str(subcontext or '').strip('/')

    paths = []
    rel_dirs = {}
    for item in raw_items:
        rel_norm = os.path.normpath(item.replace('\\', '/')).lstrip('/\\')
        if not rel_norm or rel_norm in ('.', '..') or rel_norm.startswith('..'):
            raise ValueError('Invalid staged upload path')
        full_path = os.path.abspath(os.path.join(base_dir, rel_norm))
        if os.path.commonpath([base_dir, full_path]) != base_dir:
            raise ValueError('Invalid staged upload path')
        if not os.path.exists(full_path):
            alt_path = os.path.abspath(os.path.join(base_dir, os.path.basename(rel_norm)))
            if os.path.commonpath([base_dir, alt_path]) == base_dir and os.path.exists(alt_path):
                full_path = alt_path
            else:
                raise ValueError(f'File [{item}] does not exist in staged uploads')
        if os.path.isdir(full_path):
            for root, _dirnames, filenames in sorted(os.walk(full_path)):
                for filename in sorted(filenames):
                    member = os.path.abspath(os.path.join(root, filename))
                    paths.append(member)
                    rel_dirs[member] = os.path.relpath(root, base_dir).replace('\\', '/').strip('.')
        else:
            paths.append(full_path)
            rel_dirs[full_path] = os.path.dirname(rel_norm).replace('\\', '/').strip('.')
    if not paths:
        raise ValueError('Select at least one file')

    if not sobject.get_value('code', no_exception=True):
        sobject.set_value('code', os.path.basename(paths[0]))
        sobject.commit()

    snapshots = []
    if checkin_mode in ('file_group', 'file'):
        folder_part = rel_dirs.get(paths[0], '').strip('/')
        if subcontext_mode == '{folder}' and folder_part:
            checkin_context = f"{context}/{folder_part.replace('/', '_')}"
        elif subcontext:
            checkin_context = f'{context}/{subcontext}'
        else:
            checkin_context = context
        file_types = [f'ingest{idx}' for idx in range(len(paths))]
        checkin = FileCheckin(
            sobject,
            file_paths=paths,
            file_types=file_types,
            context=checkin_context,
            mode=transfer_mode,
            description=f'Ingest Files as group check-in [{sobject.get_code()}]',
        )
        checkin.execute()
        if checkin.get_snapshot():
            snapshots.append(checkin.get_snapshot())
    elif subcontext_mode == '{none}' and not subcontext:
        used_types = set()
        file_types = []
        for idx, path in enumerate(paths):
            ext = os.path.splitext(path)[1].lstrip('.') or 'main'
            file_type = ext if ext not in used_types else f'{ext}_{idx}'
            used_types.add(file_type)
            file_types.append(file_type)
        checkin = FileCheckin(
            sobject,
            file_paths=paths,
            file_types=file_types,
            context=context,
            mode=transfer_mode,
            description=f'Ingest check-in [{sobject.get_code()}]',
        )
        checkin.execute()
        if checkin.get_snapshot():
            snapshots.append(checkin.get_snapshot())
    else:
        for path in paths:
            folder_part = rel_dirs.get(path, '').strip('/')
            if subcontext_mode == '{leaf}':
                checkin_context = f'{context}/{os.path.basename(path)}'
            elif subcontext_mode == '{folder}' and folder_part:
                checkin_context = f"{context}/{folder_part.replace('/', '_')}"
            elif subcontext:
                checkin_context = f'{context}/{subcontext}'
            else:
                checkin_context = context
            checkin = FileCheckin(
                sobject,
                file_paths=[path],
                file_types=['main'],
                context=checkin_context,
                mode=transfer_mode,
                description=f'Ingest file [{os.path.basename(path)}]',
            )
            checkin.execute()
            if checkin.get_snapshot():
                snapshots.append(checkin.get_snapshot())

    return dict(
        search_key=sobject.get_search_key(),
        code=sobject.get_code(),
        snapshot_codes=[snap.get_code() for snap in snapshots],
        file_count=len(paths),
    )


class FileIngestCmd(DatabaseAction):

    def get_title(self):
        return 'Ingest Files'

    def execute(self):
        search_key = self.kwargs.get('search_key') or (self.sobject.get_search_key() if self.sobject else '')
        result = ingest_drop_files(
            search_key=search_key,
            files=self.kwargs.get('files') or self.get_option('files'),
            dirs=self.kwargs.get('dirs') or self.get_option('dirs'),
            upload_directory=self.kwargs.get('upload_directory') or self.get_option('upload_directory'),
            transfer_mode=self.kwargs.get('transfer_mode') or self.get_option('transfer_mode'),
            checkin_mode=self.kwargs.get('checkin_mode') or self.get_option('checkin_mode'),
            context=self.kwargs.get('context') or self.get_option('context'),
            subcontext_mode=self.kwargs.get('subcontext_mode') or self.get_option('subcontext_mode'),
            subcontext=self.kwargs.get('subcontext') or self.get_option('subcontext'),
        )
        self.info.update(result)
        self.add_description(f"Ingested {result['file_count']} file(s) into [{result['code']}]")

    def post_execute(self):
        if self.sobject and not self.info.get('snapshot_codes') and (self.get_option('files') or self.get_option('dirs')):
            self.execute()


__all__ = ['FileIngestCmd', 'ingest_drop_files']
