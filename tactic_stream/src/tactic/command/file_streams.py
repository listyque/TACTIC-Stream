"""Editable stream specifications; published branch ancestry remains immutable."""
from time import time_ns

from pyasm.biz.file_project import find, save
from pyasm.common import Environment
from pyasm.common.errors import SecurityException


STREAM_TYPES = ('mainline', 'development', 'release')


class FileStreamMixin:
    def stream_spec(self, item):
        data = self.result(item)
        return {**data, 'title': data.get('title') or item.get_code(),
                'description': data.get('description', ''),
                'owner': data.get('owner') or item.get_value('login'),
                'stream_type': data.get('stream_type') or ('development' if data.get('parent') else 'mainline'),
                'spec_revision': data.get('spec_revision', 0), 'locked': data.get('locked', False)}

    def validate_stream_spec(self, code, depot, previous=None):
        from .file_project_cmd import identifier
        values = self.kwargs
        data = dict(previous or {})
        for key, limit in (('title', 1024), ('description', 16384)):
            value = values.get(key, data.get(key, code if key == 'title' else ''))
            if not isinstance(value, str) or len(value.encode('utf-8')) > limit or '\0' in value:
                raise ValueError('Invalid stream ' + key)
            data[key] = value
        locked = values.get('locked', data.get('locked', False))
        if not isinstance(locked, bool):
            raise ValueError('Stream locked must be a boolean')
        data['locked'] = locked
        parent = values.get('parent', data.get('parent')) or None
        kind = values.get('stream_type', data.get('stream_type') or ('development' if parent else 'mainline'))
        if kind not in STREAM_TYPES:
            raise ValueError('Supported stream types: mainline, development, release. Virtual/task views are not implemented.')
        if (kind == 'mainline') != (parent is None):
            raise ValueError('Mainline has no parent; development and release require a parent')
        if previous and kind != previous['stream_type']:
            raise ValueError('Changing an existing stream type is not supported')
        seen = {code}
        ancestor = parent
        while ancestor:
            identifier(ancestor)
            if ancestor in seen or len(seen) >= 256:
                raise ValueError('Stream parent would create a cycle or exceed 255 ancestors')
            seen.add(ancestor)
            item, info = self.stream(ancestor)
            if info['depot'] != depot:
                raise ValueError('Parent must belong to the same depot')
            if ancestor == parent and self.stream_spec(item)['stream_type'] not in ('mainline', kind):
                raise ValueError('Parent must be a mainline or the same stream type')
            ancestor = info.get('parent')
        data.update(parent=parent, stream_type=kind)
        return data

    def update_stream(self):
        from .file_project_cmd import identifier, integer
        code = identifier(self.kwargs.get('stream'))
        _, current = self.stream(code, 'write')
        # Serialize topology edits in a depot so concurrent reparenting cannot form a cycle.
        self.lock('depot', current['depot'])
        item, current = self.stream(code, 'write', lock=True)
        spec = self.stream_spec(item)
        if spec['locked'] and spec['owner'] != self.owner and not Environment.get_security().is_admin():
            raise SecurityException('Only the stream owner or an administrator may edit its locked settings')
        revision = integer(self.kwargs.get('spec_revision'))
        if revision != spec['spec_revision']:
            raise ValueError('Stream settings changed; reload the editor before saving')
        data = self.validate_stream_spec(code, current['depot'], spec)
        data.pop('code', None)
        data.setdefault('branch_parent', current.get('parent'))
        data.update(spec_revision=revision + 1, spec_updated_at=time_ns()//1000)
        save(item, data)
        return self.stream_spec(item)
