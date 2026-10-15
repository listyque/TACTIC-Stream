"""Indexed published revision selection for browsing and pinned workspace sync."""
from datetime import datetime, timezone, timedelta

from pyasm.biz import Project
from pyasm.biz.file_project import create, find, save, stamp, revision_schema
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin

SELECTORS = ('revision', 'changelist', 'at_date', 'file_revision')


def revision_spec(values):
    from .file_project_cmd import integer
    spec = {key: values[key] for key in SELECTORS if values.get(key) not in (None, '')}
    if len(spec) > 1:
        raise ValueError('Choose one revision, changelist or date selector')
    for key in ('revision', 'file_revision'):
        if key in spec:
            spec[key] = integer(spec[key], 1 if key == 'file_revision' else 0, 2**63 - 1)
    if 'changelist' in spec:
        value=str(spec['changelist'])
        spec['changelist']='#'+value if value.isdigit() else value
    if 'at_date' in spec:
        value = spec['at_date']
        if not isinstance(value, str) or len(value) > 64:
            raise ValueError('Choose an ISO date/time')
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        if len(value) == 10:
            date += timedelta(days=1, microseconds=-1)
        spec['at_date'] = date.astimezone(timezone.utc).isoformat()
    return spec


class FileRevisionMixin:
    def revision_upgrade(self):
        """Admin-only native schema upgrade and resumable 1000-record backfill."""
        from .file_storage import maintenance
        _require_admin()
        revision_schema(Project.get().get_project_db_resource().get_sql())
        record = find('chunk', 'revision-index', False)
        if record is None:
            record = create('chunk', {'table':'change','after':0,'complete':False}, 'revision-index')
        else:
            record = self.lock('chunk', 'revision-index')
        progress = record.get_json_value('data')
        if progress['complete']:
            return progress
        search = Search('file_project/' + progress['table'])
        search.add_filter('id', progress['after'], op='>')
        search.add_order_by('id'); search.set_limit(1000)
        rows = search.get_sobjects()
        with maintenance(self.project):
            for row in rows:
                data = row.get_json_value('data')
                if progress['table'] == 'change' and data['state'] == 'submitted' and not data.get('submitted_at'):
                    data['submitted_at'] = int(row.get_value('updated_at', no_exception=True) or row.get_value('created_at', no_exception=True) or 0) * 1000000
                    row.set_json_value('data', data)
                stamp(row, data); row.commit()
                progress['after'] = row.get_id()
        if len(rows) < 1000:
            if progress['table'] == 'change':
                progress.update(table='version', after=0)
            else:
                progress['complete'] = True
        save(record, progress)
        return progress

    def revision_snapshot(self):
        from .file_project_cmd import logical_path
        stream_code = self.kwargs['stream']
        _, stream = self.stream(stream_code)
        spec = revision_spec(self.kwargs)
        if not spec:
            return {'stream':stream_code,'root':stream['root'],'published_change':stream['head_change'],'revision':stream['revision']}
        index=find('chunk','revision-index',False)
        if not SearchType.column_exists('file_project/change', 'submitted_at') or index is not None and not index.get_json_value('data').get('complete'):
            raise ValueError('Run revision_upgrade before selecting historical revisions')
        if 'file_revision' in spec:
            path = logical_path(self.kwargs.get('path'))
            head = self.catalog.get(stream['root'], path)
            selected, _ = self.file_revisions([head], spec['file_revision'], stream_code) if head else ({}, [])
            entry = selected.get(path)
            if entry is None:
                raise ValueError('No published file revision at this path')
            version = find('version', entry['version']).get_json_value('data')
            return {'stream':stream_code,'root':self.catalog.update(self.catalog.empty(), [entry]),
                    'published_change':version['change'],'file_revision':spec['file_revision'],'path':path}
        if 'changelist' in spec:
            change = find('change',self.change_reference(str(spec['changelist'])))
            data = change.get_json_value('data')
            if data['state']!='submitted' or data['stream']!=stream_code:
                raise ValueError('Choose a submitted changelist in the selected stream')
        else:
            search = Search('file_project/change')
            search.add_filter('stream_code',stream_code);search.add_filter('state','submitted')
            if 'revision' in spec:
                search.add_filter('submitted_revision',spec['revision'])
            else:
                date = datetime.fromisoformat(spec['at_date'])
                epoch = datetime(1970,1,1,tzinfo=timezone.utc)
                delta = date-epoch
                cutoff=(delta.days*86400+delta.seconds)*1000000+delta.microseconds
                search.add_filter('submitted_at',cutoff,op='<=')
            search.add_order_by('submitted_at desc');search.add_order_by('submitted_revision desc');search.set_limit(1)
            change = search.get_sobject()
            if change is None:
                if 'at_date' in spec:return {'stream':stream_code,'root':self.catalog.empty(),'published_change':None,'revision':None}
                raise ValueError('No submitted stream state at this revision or date')
            data=change.get_json_value('data')
        return {'stream':stream_code,'root':data['root'],'published_change':change.get_code(),
                'revision':data['submitted_revision'],'submitted_at':data.get('submitted_at')}

    def sync_source(self, code):
        old = self.kwargs
        try:
            self.kwargs = {key:value for key,value in old.items() if key!='file_revision'}
            self.kwargs['stream']=code
            return self.revision_snapshot()
        finally:
            self.kwargs = old

    def file_revisions(self, files, number, code):
        """Resolve a bounded path batch using version/change indexes, including forks."""
        index=find('chunk','revision-index',False)
        if not SearchType.column_exists('file_project/version','number') or index is not None and not index.get_json_value('data').get('complete'):
            raise ValueError('Run revision_upgrade before selecting file revisions')
        remaining={file['path']:file for file in files}
        resolved={}
        visited=set()
        while remaining and code not in visited:
            visited.add(code)
            paths=[path for path,file in remaining.items() if file.get('number',0)>=number]
            if not paths:break
            after=''
            while True:
                search=Search('file_project/version')
                search.add_filter('stream_code',code);search.add_filters('path',paths);search.add_filter('number',number)
                if after:search.add_filter('code',after,op='>')
                search.add_order_by('code');search.set_limit(1000)
                rows=search.get_sobjects()
                candidates=[row.get_json_value('data') for row in rows]
                changes=Search('file_project/change')
                changes.add_filters('code',list({row['change'] for row in candidates}))
                changes.add_filter('state','submitted')
                published={row.get_code():row.get_json_value('data') for row in changes.get_sobjects()} if candidates else {}
                for candidate in candidates:
                    change=published.get(candidate['change'])
                    if not change:continue
                    entry=self.catalog.get(change['root'],candidate['path'])
                    if entry and entry['version']==candidate['version']:
                        resolved[candidate['path']]=entry
                        remaining.pop(candidate['path'],None)
                if len(rows)<1000:break
                after=rows[-1].get_code()
            stream=find('stream',code).get_json_value('data')
            if not stream.get('parent'):break
            inherited={path:self.catalog.get(stream['fork_root'],path) for path in remaining}
            remaining={path:file for path,file in inherited.items() if file and file['number']>=number}
            code=stream['parent']
        return resolved, [file['path'] for file in files if file['path'] not in resolved]
