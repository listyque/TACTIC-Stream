"""Submit review and options for the desktop file workspace."""
from itertools import islice
from hashlib import sha256
import uuid

from pyasm.biz.file_project import find, encode, save_batch
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.search import Search


def can_read_change(data):
    return not data.get('restricted') or data['owner'] == Environment.get_user_name() or Environment.get_security().is_admin()


class FileSubmitMixin:
    can_read_change_metadata = staticmethod(can_read_change)

    def submit_tasks(self):
        from .file_project_cmd import integer
        from tactic.ui.table.task_element_wdg import TaskElementWdg
        from tactic.ui.table.task_inspector import task_fields, task_status_names
        _, change = self.change(lock=False)
        fields = {field['name']: field for field in task_fields()}
        search = Search('sthpw/task')
        search.add_filter('project_code', self.project)
        if self.kwargs.get('after'):
            after = self.kwargs['after']
            search.add_filter('id', integer(int(after) if isinstance(after, str) and after.isdecimal() else after), op='>')
        query = self.kwargs.get('query', '')
        if not isinstance(query, str) or len(query) > 256:
            raise ValueError('Task search must be at most 256 characters')
        if query:
            if 'description' in fields:
                search.add_op('begin')
                search.add_filter('code', '%' + query + '%', op='like')
                search.add_filter('description', '%' + query + '%', op='like')
                search.add_op('or')
            else:
                search.add_filter('code', '%' + query + '%', op='like')
        search.add_order_by('id')
        search.set_limit(101)
        rows = search.get_sobjects()
        def task_info(row):
            return dict(code=row.get_code(), description=(row.get_value('description') or '') if 'description' in fields else '',
                      status=(row.get_value('status') or '') if 'status' in fields else '',
                      revision=sha256(encode(row.get_data()).encode()).hexdigest(),
                      statuses=[dict(value=name, label=row.get_pipeline().get_process(name).get_label() or name) for name in task_status_names(row)] if fields.get('status', {}).get('editable') else [])
        items = [task_info(row) for row in rows[:100] if TaskElementWdg.can_view_process(row.get_value('process') or 'publish')]
        result = {'items': items, 'after': str(rows[99].get_id()) if len(rows) > 100 else None}
        if not query and not self.kwargs.get('after'):
            linked = Search('sthpw/task')
            linked.add_filter('project_code', self.project)
            linked.add_filters('code', change.get('task_codes', []))
            result['linked'] = [task_info(row) for row in linked.get_sobjects() if TaskElementWdg.can_view_process(row.get_value('process') or 'publish')] if change.get('task_codes') else []
        return result

    def submit_shelves(self):
        """Bound scanning as well as output; shelves retain their own identities."""
        item, data = self.change(lock=False)
        return self.related_shelves(item.get_code(), self.kwargs.get('after'), owner=self.owner)

    def related_shelves(self, change, after=None, owner=None):
        from .file_project_cmd import integer
        search = Search('file_project/change')
        if owner:
            search.add_filter('login', owner)
        search.add_filter('state', 'shelved')
        if after:
            search.add_filter('id', integer(int(after) if isinstance(after, str) and after.isdecimal() else after), op='>')
        search.add_order_by('id'); search.set_limit(101)
        rows = search.get_sobjects()
        items = []
        for shelf in rows[:100]:
            value = shelf.get_json_value('data')
            if value.get('source_change') == change and not value.get('archived_shelf') and can_read_change(value):
                items.append({**self.result(shelf), 'files': self.catalog.stats(value['work_root'])['files']})
        return {'items': items, 'after': str(rows[99].get_id()) if len(rows) > 100 else None}

    def submit_settings(self, data):
        from .file_project_cmd import identifier
        from tactic.ui.table.task_element_wdg import TaskElementWdg
        description = self.kwargs.get('description', data.get('description', ''))
        if not isinstance(description, str) or len(description.encode('utf-8')) > 4096:
            raise ValueError('Description must be text of at most 4096 UTF-8 bytes')
        restricted = self.kwargs.get('restricted', data.get('restricted', False))
        if not isinstance(restricted, bool):
            raise ValueError('restricted must be boolean')
        codes = self.kwargs.get('task_codes', data.get('task_codes', []))
        if not isinstance(codes, list) or len(codes) > 100:
            raise ValueError('Choose at most 100 linked tasks')
        codes = list(dict.fromkeys(identifier(code) for code in codes))
        if codes:
            search = Search('sthpw/task'); search.add_filter('project_code', self.project); search.add_filters('code', codes)
            tasks = search.get_sobjects()
            if len(tasks) != len(codes) or any(not TaskElementWdg.can_view_process(task.get_value('process') or 'publish') for task in tasks):
                raise SecurityException('A linked task is missing or not accessible in this project')
        updates = self.kwargs.get('task_status_updates', data.get('task_status_updates', []))
        if not isinstance(updates, list) or len(updates) > 100:
            raise ValueError('Choose at most 100 task status updates')
        by_code = {task.get_code(): task for task in tasks} if codes else {}
        seen = set()
        from tactic.ui.table.task_inspector import task_fields, task_status_names
        if updates and not any(field['name'] == 'status' and field['editable'] for field in task_fields()):
            raise SecurityException('Task status is read-only')
        for update in updates:
            if not isinstance(update, dict) or set(update) != {'code', 'status', 'revision'} or update['code'] not in by_code or update['code'] in seen:
                raise ValueError('Choose each linked task status once')
            task = by_code[update['code']]; seen.add(update['code'])
            if update['status'] not in task_status_names(task):
                raise SecurityException('Task status is not available in its workflow')
            if update['revision'] != sha256(encode(task.get_data()).encode()).hexdigest():
                raise ValueError('A linked task changed; refresh the task selection')
        return dict(description=description, restricted=restricted, task_codes=codes, task_status_updates=updates)

    def submit_task_status(self):
        """After publication, update tasks through their native command lifecycle."""
        from tactic.ui.table.task_inspector import task_fields, task_status_names
        from tactic.ui.table.task_element_wdg import TaskElementWdg
        _, data = self.change(lock=False, pending=False)
        if data['state'] != 'submitted':
            raise ValueError('Publish the changelist before updating linked tasks')
        updates = data.get('task_status_updates', [])
        if not updates:
            return {'updated': 0}
        if not any(field['name'] == 'status' and field['editable'] for field in task_fields()):
            raise SecurityException('Task status is read-only')
        search = Search('sthpw/task'); search.add_filter('project_code', self.project)
        search.add_filters('code', [row['code'] for row in updates])
        tasks = {row.get_code(): row for row in search.get_sobjects()}
        pending = []
        for update in sorted(updates, key=lambda row: row['code']):
            task = tasks.get(update['code'])
            if task is None or not TaskElementWdg.can_view_process(task.get_value('process') or 'publish'):
                raise SecurityException('Linked task is missing or inaccessible')
            task.get_sql().lock_sobject(task, timeout=5000)
            task = Search.get_by_code('sthpw/task', task.get_code())
            if task.get_value('project_code') != self.project:
                raise SecurityException('Linked task belongs to another project')
            if update['status'] not in task_status_names(task):
                raise SecurityException('Task status is no longer available')
            if task.get_value('status') == update['status']:
                continue
            if sha256(encode(task.get_data()).encode()).hexdigest() != update['revision']:
                raise ValueError('Linked task changed after review: ' + task.get_code())
            pending.append((task, update['status']))
        for task, status in pending:
            task.set_value('status', status); task.commit()
        return {'updated': len(pending)}

    def submit_options(self, change, data):
        """Repartition using existing native commands; no intermediate changes commit."""
        from .file_project_cmd import CHUNK_LIMIT, logical_path
        options = self.kwargs.get('submit_options', {})
        if not isinstance(options, dict) or set(options) - {'selection_all', 'selection_paths', 'unchanged', 'reopen', 'guard_resolved'}:
            raise ValueError('Invalid submit options')
        all_files = options.get('selection_all', True)
        reopen = options.get('reopen', False)
        guard = options.get('guard_resolved', False)
        if any(not isinstance(value, bool) for value in (all_files, reopen, guard)):
            raise ValueError('Submit checkboxes must be boolean')
        paths = options.get('selection_paths', [])
        if not isinstance(paths, list) or len(paths) > CHUNK_LIMIT:
            raise ValueError('Choose at most 1000 explicit selection exceptions')
        paths = set(logical_path(path) for path in paths)
        if any(not self.catalog.get(data['work_root'], path) for path in paths):
            raise ValueError('The selection includes a file outside this changelist')
        self.complete_renames(data, list(paths)) if paths else None
        policy = options.get('unchanged', 'submit')
        if policy not in ('submit', 'revert', 'leave'):
            raise ValueError('Choose a valid unchanged-file policy')
        original = self.kwargs
        remainder = None
        cursor = iter(self.catalog.entries(data['work_root']))
        try:
            while rows := list(islice(cursor, CHUNK_LIMIT // 2)):
                move, remove, promote, versions = set(), set(), [], []
                for row in rows:
                    path = row['path']
                    selected = (path not in paths) if all_files else (path in paths)
                    file, base = row.get('file') or {}, row.get('base') or {}
                    unchanged = bool(base) and not row['action'].startswith('move/') and all(file.get(key) == base.get(key) for key in ('sha256', 'size', 'deleted'))
                    if selected and guard and 'resolved_sha256' in row and row['resolved_sha256'] != file.get('sha256'):
                        raise ValueError('A resolved file changed after resolution: ' + path)
                    if selected and unchanged and policy == 'submit' and row['action'] == 'checkout':
                        promote.append({**row, 'file': self.version_entry(path, file, base, change.get_code(), data['stream'], versions), 'action': 'write', 'size': file['size']})
                    target = move if not selected or unchanged and policy == 'leave' else remove if unchanged and policy == 'revert' else None
                    if target is not None:
                        target.add(path)
                        partner = file.get('moved_from') or file.get('moved_to')
                        if partner: target.add(partner)
                current = find('change', change.get_code()).get_json_value('data')
                if promote:
                    save_batch('version', versions)
                    current['root'] = self.catalog.update(current['root'], [row['file'] for row in promote])
                    current['work_root'] = self.catalog.update(current['work_root'], promote)
                    current['edit_revision'] += 1
                    self.save_change(change, current)
                move = [path for path in sorted(move) if self.catalog.get(current['work_root'], path)]
                if move:
                    if remainder is None:
                        self.kwargs = dict(workspace=data['workspace'], stream=data['stream'], description=data.get('description', ''))
                        remainder = self.create_change()
                    self.kwargs = dict(change=change.get_code(), edit_revision=current['edit_revision'], target_change=remainder['code'],
                                       target_edit_revision=remainder['edit_revision'], paths=move, request_id=uuid.uuid4().hex)
                    result = self.move_files(); remainder = result['target']; current = result['source']
                if remove:
                    self.kwargs = dict(change=change.get_code(), edit_revision=current['edit_revision'], paths=sorted(remove), request_id=uuid.uuid4().hex)
                    self.remove_files()
        finally:
            self.kwargs = original
        data = find('change', change.get_code()).get_json_value('data')
        if not self.catalog.stats(data['work_root'])['files']:
            raise ValueError('No files selected for submit after applying the unchanged-file policy')
        return data, remainder, reopen

    def finish_submit_options(self, data, head, remainder, reopen):
        if remainder:
            item = find('change', remainder['code']); value = item.get_json_value('data')
            root = head['root']
            cursor = iter(self.catalog.entries(value['work_root']))
            while rows := list(islice(cursor, 1000)):
                root = self.catalog.update(root, [row['file'] for row in rows if row.get('file')])
            value.update(base_root=head['root'], base_revision=head['revision'], root=root)
            self.save_change(item, value)
        if reopen:
            original = self.kwargs
            try:
                cursor = iter(self.catalog.entries(data['work_root']))
                while rows := list(islice(cursor, 1000)):
                    for mode in ('ordinary', 'exclusive'):
                        paths = [row['path'] for row in rows if not (row.get('file') or {}).get('deleted') and row.get('mode', 'ordinary') == mode]
                        if paths:
                            if remainder is None:
                                self.kwargs = dict(workspace=data['workspace'], stream=data['stream'], description=data.get('description', ''))
                                remainder = self.create_change()
                            self.kwargs = dict(change=remainder['code'], paths=paths, mode=mode)
                            self.checkout()
            finally:
                self.kwargs = original
        return remainder['code'] if remainder else None
