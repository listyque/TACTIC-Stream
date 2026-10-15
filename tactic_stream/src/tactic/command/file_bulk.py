"""Queued pinned selections, bounded native mutations, one atomic transaction."""
from itertools import islice
from time import time, monotonic
import uuid

from pyasm.biz.file_project import create, find, save
from pyasm.biz.file_job_signals import FileJobSignals
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import _context
from .file_transfer import service_only

BULK_ACTIONS = {'bulk_begin', 'bulk_status', 'bulk_tasks', 'bulk_items', 'bulk_cancel',
                'bulk_claim', 'bulk_run', 'bulk_fail', 'bulk_block'}
BULK_OPERATIONS = {'checkout', 'move_files', 'remove_files', 'mark_delete'}


class FileBulkMixin:
    def bulk_signals(self, code):
        return FileJobSignals(_context.get().store.data_dir, self.project, code)

    def bulk_workspace_index(self, data, task, remove=False):
        workspace=self.lock('workspace',data['workspace'])
        value=workspace.get_json_value('data')
        value['active_bulk_root']=self.catalog.update(value.get('active_bulk_root') or self.catalog.empty(),
            [{'path':task,'delete':True} if remove else {'path':task,'size':0}])
        self.save_change(workspace,value)

    def bulk_job(self, lock=False, admin=False):
        from .file_project_cmd import identifier
        code = identifier(self.kwargs.get('task'))
        item = self.lock('sync', code) if lock else find('sync', code)
        data = item.get_json_value('data')
        if data.get('kind') != 'mutation' or data['state'] == 'expired':
            raise ValueError('Active bulk mutation task required')
        if admin:
            from pyasm.security.security import _require_admin
            _require_admin()
        elif data['owner'] != self.owner:
            raise SecurityException('Bulk task belongs to another user')
        return item, data

    def bulk_public(self, item, data=None):
        data = data or item.get_json_value('data')
        result = {key:value for key,value in data.items() if key not in ('selection_snapshot','worker_token')}
        result['task'] = item.get_code()
        if data['state'] == 'running':
            progress = self.bulk_signals(item.get_code()).read()
            if progress.get('worker_token') == data.get('worker_token'):
                result.update({key:progress[key] for key in ('files_done','scanned_files','path','phase','heartbeat') if key in progress})
        result['cancel_requested'] = self.bulk_signals(item.get_code()).cancelled()
        return result

    def bulk_begin(self):
        from .file_project_cmd import integer
        operation = self.kwargs.get('operation')
        if operation not in BULK_OPERATIONS:
            raise ValueError('Choose checkout, move, remove/revert or mark-delete')
        selected = self.selected_query()
        probe, initial = self.change(lock=False,pending=False)
        self.stream(initial['stream'],'write',lock=True)
        key, digest, retry = self.receipt(probe.get_code(), 'bulk_begin')
        if retry is not None:
            return self.bulk_status_for(retry['task'])
        item, data = self.mutation()
        self.editable(data)
        self.revision(data)
        if selected['source'] in ('depot','change') and selected['reference']['stream'] != data['stream']:
            raise ValueError('Choose a changelist in the selected stream')
        if operation != 'checkout' and (selected['source'] != 'change' or selected['reference']['change'] != item.get_code()):
            raise ValueError('Select this pending changelist for move/remove/delete')
        if selected['source'] == 'change' and selected['reference']['edit_revision'] != data['edit_revision']:
            raise ValueError('Selection is stale; select the pending files again')
        if selected['source'] == 'depot' and selected['root'] != data['base_root']:
            raise ValueError('Rebase to the selected depot snapshot before checkout')
        if selected['source'] == 'have' and selected['reference']['workspace'] != data['workspace']:
            raise ValueError('Have selection must belong to this workspace')
        mode = self.kwargs.get('mode', 'ordinary')
        if mode not in ('ordinary','exclusive'):
            raise ValueError('Choose ordinary or exclusive checkout')
        target = None
        if operation == 'move_files':
            target = self.change_reference(self.kwargs.get('target_change'))
            if target == item.get_code():
                raise ValueError('Source and target changelists must differ')
            destination = self.lock('change', target)
            dest = destination.get_json_value('data')
            if dest['owner'] != self.owner or dest['state'] != 'pending' or dest['stream'] != data['stream'] or dest['workspace'] != data['workspace']:
                raise SecurityException('Choose an owned pending target in this workspace and stream')
            self.editable(dest)
            if integer(self.kwargs.get('target_edit_revision')) != dest['edit_revision']:
                raise ValueError('Target changelist edit revision conflict')
        count = self.catalog.prefix_stats(selected['root'], selected['prefix']) if not any(selected.get(key) for key in ('name','file_action','start_path','end_path')) else {'files':None,'bytes':None}
        task = create('sync', {'kind':'mutation','owner':self.owner,'state':'queued','phase':'queued',
            'stream':data['stream'],'workspace':data['workspace'],'change':item.get_code(),
            'operation':operation,'mode':mode,'selection_snapshot':selected,
            'edit_revision':data['edit_revision'],'target_change':target,
            'target_edit_revision':dest['edit_revision'] if target else None,
            'files_done':0,'scanned_files':0,'files_total':count['files'],
            'total_known':count['files'] is not None,'lease_until':0,'created':time()})
        data['active_bulk'] = task.get_code()
        self.save_change(item, data)
        if target:
            dest['active_bulk'] = task.get_code()
            self.save_change(destination, dest)
        self.bulk_workspace_index(data,task.get_code())
        self.remember(key, digest, {'task':task.get_code()})
        return self.bulk_public(task)

    def bulk_status_for(self, code):
        old = self.kwargs
        try:
            self.kwargs = {'task':code}
            return self.bulk_status()
        finally:
            self.kwargs = old

    def bulk_status(self):
        item, data = self.bulk_job()
        self.stream(data['stream'])
        return self.bulk_public(item, data)

    def bulk_tasks(self):
        from .file_project_cmd import integer, identifier
        limit = integer(self.kwargs.get('limit',200),1,1000)
        search = Search('file_project/sync')
        search.add_filter('kind','mutation')
        search.add_filter('login',self.owner)
        search.add_order_by('code')
        if self.kwargs.get('after'):
            search.add_filter('code',identifier(self.kwargs['after']),op='>')
        search.set_limit(limit+1)
        rows = search.get_sobjects()
        return {'items':[self.bulk_public(row) for row in rows[:limit]],
                'after':rows[limit-1].get_code() if len(rows)>limit else None}

    def bulk_items(self):
        from .file_project_cmd import integer, logical_path
        item, data = self.bulk_job()
        snapshot = data['selection_snapshot']
        limit = integer(self.kwargs.get('limit',200),1,1000)
        after = logical_path(self.kwargs.get('after',''),prefix=True)
        page = list(islice(self.selection_entries(snapshot,after),limit+1))
        rows = [row for row in page[:limit] if self.selection_matches(snapshot,row)]
        for stream in sorted({row.get('stream',data['stream']) for row in rows}):
            self.stream(stream)
        status = self.bulk_public(item,data)
        state = 'rolled_back' if data['state'] in ('error','cancelled') else data['state']
        return {'task':item.get_code(),'items':[{**row,'state':state} for row in rows],
                'after':page[limit-1]['path'] if len(page)>limit else None,'state':data['state'],'error':data.get('error')}

    def bulk_cancel(self):
        item, data = self.bulk_job()
        if data['state'] in ('queued','running'):
            # A cancellation signal must remain writable while SQLite holds the atomic write transaction.
            self.bulk_signals(item.get_code()).cancel()
        return self.bulk_public(item, data)

    def bulk_claim(self):
        service_only()
        item, data = self.bulk_job(lock=True)
        if data['state'] not in ('queued','running'):
            return self.bulk_public(item, data)
        if data['state'] == 'running':
            heartbeat=self.bulk_signals(item.get_code()).read()
            live=heartbeat.get('worker_token')==data.get('worker_token') and heartbeat.get('heartbeat',0)+60>time()
            if data['lease_until'] > time() or live:
                raise ValueError('Bulk task already claimed')
        data.update(state='running',phase='applying',lease_until=time()+60,worker_token=uuid.uuid4().hex)
        save(item,data)
        return {'task':item.get_code(),'worker_token':data['worker_token']}

    def bulk_worker(self):
        service_only()
        item, data = self.bulk_job(lock=True)
        if data.get('worker_token') != self.kwargs.get('worker_token') or data['state'] != 'running':
            raise ValueError('Bulk worker lease changed')
        return item, data

    def bulk_run(self):
        from .file_project_cmd import CHUNK_LIMIT
        from .file_change import identity
        item, job = self.bulk_worker()
        control = self.bulk_signals(item.get_code())
        snapshot = job['selection_snapshot']
        original = self.kwargs
        self._bulk_job = item.get_code()
        revision, target_revision = job['edit_revision'], job['target_edit_revision']
        last_report, processed, scanned, chunk = 0, 0, 0, 0
        try:
            self.kwargs = {'change':job['change']}
            change, current = self.mutation()
            if current.get('active_bulk') != item.get_code() or current['edit_revision'] != revision:
                raise ValueError('Bulk source changed before execution')
            if job['target_change']:
                target = self.lock('change',job['target_change'])
                dest = target.get_json_value('data')
                if dest.get('active_bulk') != item.get_code() or dest['edit_revision'] != target_revision:
                    raise ValueError('Bulk target changed before execution')
            entries = iter(self.selection_entries(snapshot))
            while True:
                if control.cancelled() or (getattr(self,'_bulk_stopped',lambda:False))():
                    raise InterruptedError('Bulk operation cancelled; the entire transaction was rolled back')
                page = list(islice(entries,CHUNK_LIMIT))
                if not page:
                    break
                scanned += len(page)
                selected = [row for row in page if self.selection_matches(snapshot,row)]
                paths = [row.get('source_path',row['path']) for row in selected]
                if any(row.get('stream',job['stream']) != job['stream'] for row in selected):
                    raise ValueError('Bulk selection spans different streams')
                if job['operation']=='checkout' and snapshot['source']=='have':
                    for row in selected:
                        base=self.catalog.get(current['base_root'],row.get('source_path',row['path']))
                        if identity(row)!=identity(base):
                            raise ValueError('Have revision differs from changelist base; sync or rebase first: '+row['path'])
                if paths:
                    # Complete rename pairs are one operation even across catalog page boundaries.
                    if snapshot['source'] == 'change':
                        partners = []
                        for row in selected:
                            file = row.get('file') or {}
                            partner = file.get('moved_from') or file.get('moved_to')
                            if partner:
                                pair = self.catalog.get(snapshot['root'],partner)
                                if not pair or not self.selection_matches(snapshot,pair) or not partner.startswith(snapshot['prefix']):
                                    raise ValueError('Select both sides of the rename operation')
                                if partner < row['path']:
                                    continue
                                partners.append((row['path'],partner))
                        renamed = {path for pair in partners for path in pair}
                        paths = [path for path in paths if not (self.catalog.get(snapshot['root'],path).get('action','').startswith('move/'))]
                        batches = [paths] if paths else []
                        pair_paths = [path for pair in partners for path in pair]
                        batches += [pair_paths[offset:offset+CHUNK_LIMIT] for offset in range(0,len(pair_paths),CHUNK_LIMIT)]
                    else:
                        batches = [paths]
                    for paths in batches:
                        args = {'action':job['operation'],'change':job['change'],'edit_revision':revision,
                                'request_id':item.get_code()+'-'+str(chunk),'paths':paths}
                        if job['operation'] == 'checkout':
                            args['mode'] = job['mode']
                        elif job['operation'] == 'move_files':
                            args.update(target_change=job['target_change'],target_edit_revision=target_revision)
                        elif job['operation'] == 'mark_delete':
                            args.update(action='edit',chunk=item.get_code()+'-'+str(chunk),operations=[{'path':path,'delete':True} for path in paths])
                            args.pop('paths');args.pop('request_id')
                        self.kwargs = args
                        result = getattr(self,args['action'])()
                        if job['operation'] == 'move_files':
                            revision = result['source']['edit_revision'];target_revision = result['target']['edit_revision']
                        else:
                            revision = result['edit_revision']
                        processed += len(paths);chunk += 1
                if monotonic()-last_report >= .2:
                    control.progress({'worker_token':job['worker_token'],'files_done':processed,'scanned_files':scanned,
                                      'path':page[-1]['path'],'phase':'applying','heartbeat':time()})
                    last_report = monotonic()
            if control.cancelled():
                raise InterruptedError('Bulk operation cancelled; the entire transaction was rolled back')
            for code in (job['change'],job['target_change']):
                if code:
                    record = self.lock('change',code)
                    data = record.get_json_value('data')
                    if data.get('active_bulk') == item.get_code():
                        data.pop('active_bulk')
                        self.save_change(record,data)
            job.update(state='complete',phase='complete',files_done=processed,files_total=processed,total_known=True,scanned_files=scanned,lease_until=0,
                       edit_revision=revision,target_edit_revision=target_revision)
            self.bulk_workspace_index(job,item.get_code(),remove=True)
            save(item,job)
            return self.bulk_public(item,job)
        finally:
            self.kwargs = original

    def bulk_end_failed(self, item, data, error, cancelled):
        for code in (data['change'],data['target_change']):
            if code:
                record = self.lock('change',code)
                value = record.get_json_value('data')
                if value.get('active_bulk') == item.get_code():
                    value.pop('active_bulk')
                    self.save_change(record,value)
        data.update(state='cancelled' if cancelled else 'error',phase='cancelled' if cancelled else 'error',
                    error=error,files_done=0,lease_until=0)
        self.bulk_workspace_index(data,item.get_code(),remove=True)
        save(item,data)
        return self.bulk_public(item,data)

    def bulk_fail(self):
        item, data = self.bulk_worker()
        error = self.kwargs.get('error')
        if not isinstance(error,str):
            raise ValueError('Error description required')
        return self.bulk_end_failed(item,data,error,self.bulk_signals(item.get_code()).cancelled())

    def bulk_block(self):
        service_only()
        item, data = self.bulk_job(lock=True,admin=True)
        if data['state'] not in ('queued','running'):
            return self.bulk_public(item,data)
        return self.bulk_end_failed(item,data,str(self.kwargs.get('error','Worker access denied')),False)
