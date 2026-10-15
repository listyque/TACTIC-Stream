"""Cross-stream integration uses published snapshots and actual immutable file revisions."""
import uuid

from pyasm.biz.file_project import create, find
from pyasm.common.errors import SecurityException


class FileMergeMixin:
    def lineage(self, code):
        result, seen = [], set()
        while code:
            if code in seen or len(result) >= 256:
                raise ValueError('Invalid or excessively deep stream ancestry')
            seen.add(code)
            item = find('stream', code)
            data = item.get_json_value('data')
            result.append((code, data))
            code = data.get('branch_parent', data.get('parent'))
        return result

    def common_base(self, target, source):
        left, right = self.lineage(target), self.lineage(source)
        index = {code: position for position, (code, _) in enumerate(right)}
        for position, (code, _) in enumerate(left):
            if code not in index:
                continue
            cuts = []
            for lineage, depth in ((left, position), (right, index[code])):
                if depth:
                    child = lineage[depth - 1][1]
                    parent_change = child.get('parent_change')
                    if not parent_change or 'fork_root' not in child:
                        raise ValueError('Older branch needs verified stream_ancestry metadata before merge')
                    snapshot = find('change', parent_change).get_json_value('data')
                    if snapshot['stream'] != code or snapshot['state'] != 'submitted' or snapshot['root'] != child['fork_root']:
                        raise ValueError('Invalid published branch ancestry')
                    cuts.append((snapshot['submitted_revision'], snapshot['root']))
            if cuts:
                return min(cuts)[1]
        raise ValueError('Streams have no common ancestor; create a branch from a published stream')

    def stream_ancestry(self):
        from pyasm.security.security import _require_admin
        from .file_project_cmd import identifier
        _require_admin()
        item, data = self.stream(operation='write', lock=True)
        if data.get('parent_change'):
            raise ValueError('Verified branch ancestry is immutable')
        parent = data.get('parent')
        if not parent:
            raise ValueError('Stream is not a branch')
        self.stream(parent)
        parent_code = identifier(self.kwargs.get('parent_change'))
        baseline_code = identifier(self.kwargs.get('baseline_change'))
        snapshot = find('change', parent_code).get_json_value('data')
        baseline = find('change', baseline_code).get_json_value('data')
        if (snapshot['stream'] != parent or snapshot['state'] != 'submitted' or
                baseline['stream'] != item.get_code() or baseline['state'] != 'submitted' or
                baseline['submitted_revision'] != 0 or baseline['root'] != snapshot['root']):
            raise ValueError('Ancestry must match the real published parent snapshot and branch baseline')
        data.update(parent_change=parent_code, fork_root=snapshot['root'], baseline_change=baseline_code)
        self.save_change(item, data)
        return self.result(item)

    def merge_begin(self):
        from .file_project_cmd import identifier
        item, data = self.mutation()
        key, digest, retry = self.receipt(item.get_code(), 'merge_begin')
        if retry is not None:
            return retry
        self.editable(data)
        self.revision(data)
        code = identifier(self.kwargs.get('source_stream'))
        if code == data['stream']:
            raise ValueError('Source and target streams must differ')
        _, source = self.stream(code)
        _, head = self.stream(data['stream'], 'write')
        from .file_project_cmd import integer
        if 'preview_head_revision' in self.kwargs and integer(self.kwargs['preview_head_revision']) != head['revision']:
            raise ValueError('Stream head changed; review integration again')
        if source['depot'] != head['depot']:
            raise ValueError('Stream merge requires the same depot')
        if data['base_root'] != head['root'] or data['base_revision'] != head['revision']:
            raise ValueError('Rebase the destination before merging')
        published = self.kwargs.get('source_change', source['head_change'])
        snapshot = find('change', identifier(published)).get_json_value('data')
        if snapshot['state'] != 'submitted' or snapshot['stream'] != code:
            raise SecurityException('Merge source requires a submitted snapshot of the authorized source stream')
        if self.kwargs.get('preview_source_root') and self.kwargs['preview_source_root'] != snapshot['root']:
            raise ValueError('Source changed; review integration again')
        merged = self.catalog.get(head['merge_bases_root'], code) if head.get('merge_bases_root') else None
        base = merged['root'] if merged else self.common_base(data['stream'], code)
        if merged and snapshot['submitted_revision'] < merged['revision']:
            raise ValueError('Cannot merge a snapshot older than the last submitted integration')
        data['integration'] = {'code': uuid.uuid4().hex, 'kind': 'merge', 'source_root': snapshot['root'],
            'source_stream': code, 'source_change': published, 'source_revision': snapshot['submitted_revision'],
            'merge_base_root': base, 'integrated_source_root':base, 'head_root': head['root'], 'head_revision': head['revision'],
            'root': data['root'], 'work_root': data['work_root'], 'after': '', 'complete': False,
            'conflicts_root': self.catalog.empty(), 'acquired_root': self.catalog.empty()}
        self.save_change(item, data)
        return self.remember(key, digest, self.integration_result(item, data))

    def merge_entries(self, job):
        for path, base, file in self.catalog.diff(job['merge_base_root'], job['source_root'], job['after']):
            file = file or {'path': path, 'blob': None, 'size': 0, 'sha256': None, 'deleted': True}
            if file.get('version'):
                file = {**file, 'integrated_from': {'stream': job['source_stream'], 'version': file['version'],
                                                  'change': job['source_change']}}
            yield {'path': path, 'size': file['size'], 'base': base, 'file': file,
                   'action': 'delete' if file.get('deleted') else 'write', 'mode': 'ordinary'}
