"""Bounded agent editing through native workflow, object and check-in owners."""
from copy import deepcopy
import hashlib
import json
import re
import tempfile
from uuid import UUID, uuid5
from pathlib import Path
from xml.etree import ElementTree as ET

from pyasm.biz import Project, Pipeline
from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from .agent_request_cmd import AgentRequestCmd, identity, selected_object, text
from .agent_attachment_cmd import attachment
from .workflow_cmd import workflow_request


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()


def local_type(value):
    if not isinstance(value, str) or '/' not in value or value.split('/')[0] in ('config', 'sthpw', 'prod') or '?' in value:
        raise ValueError('Choose an entity in the current project')
    if SearchType.get(value).get_database() != Project.get_project_code():
        raise ValueError('Choose an entity in the current project')
    Search(value)
    return value


class AgentActionsCmd(AgentRequestCmd):
    def execute(self):
        _require_admin()
        if self.kwargs.get('project_code') != Project.get_project_code():
            raise ValueError('Agent editing project mismatch')
        self.sql = Search('config/trigger').get_sql()
        from pyasm.common import Environment
        self.owner = Environment.get_user_name()
        self.sql.get_database_impl().lock_collection_table(self.sql, 'spt_agent_request')
        row = self.load('spt_agent_request', identity(self.kwargs.get('request_id')))
        action = self.kwargs.get('action')
        if action == 'tasks_read':
            from tactic_stream.server.agent_tasks import read_tasks
            self.info = read_tasks(self.kwargs, row)
            return
        if action == 'operation':
            receipt = row.get('operations', {}).get(identity(self.kwargs.get('operation_id')))
            self.info = dict(status='applied', result=receipt['result']) if receipt else dict(status='not_found')
            return
        if action == 'snapshots':
            from tactic_stream.server.snapshot_browser import read_snapshot_browser
            item = selected_object(self.kwargs.get('search_key'))
            local_type(item.get_base_search_type())
            offset = self.kwargs.get('offset', 0)
            if type(offset) is not int or offset < 0:
                raise ValueError('Invalid snapshot offset')
            self.info = read_snapshot_browser(item, process=self.kwargs.get('process', ''), offset=offset)
            return
        if action == 'relations':
            from tactic_stream.server.result_items import relations, relation_search
            item = selected_object(self.kwargs.get('search_key'))
            local_type(item.get_base_search_type())
            branches = relations(item)
            target = self.kwargs.get('search_type', '')
            result = dict(relations=branches, objects=[])
            if target:
                local_type(target)
                branch = next((branch for branch in branches if branch['search_type'] == target and branch['path'] == self.kwargs.get('path', '')), None)
                if not branch:
                    raise ValueError('Choose a relationship from the project schema')
                query = relation_search(item, branch)
                offset = self.kwargs.get('offset', 0)
                if type(offset) is not int or offset < 0:
                    raise ValueError('Invalid relationship offset')
                query.set_offset(offset)
                query.set_limit(51)
                objects = query.get_sobjects()
                result.update(objects=[dict(child.get_data(), __search_key__=child.get_search_key()) for child in objects[:50]], has_next=len(objects) > 50)
            self.info = result
            return
        if action == 'workflow_read':
            search_type = local_type(self.kwargs.get('search_type'))
            catalog = json.loads(workflow_request('list', Project.get_project_code()))['catalog']
            workflows = [json.loads(workflow_request('load', Project.get_project_code(), item['identity']))
                         for item in catalog if item['searchType'] == search_type]
            objects = [selected_object(key).get_data() for key in row['document']['context']['search_keys']
                       if key.split('?')[0] == search_type]
            state = dict(search_type=search_type, columns=SearchType.get_column_info(search_type), workflows=workflows, objects=objects)
            self.info = dict(state, revision=digest(state))
            return
        if action == 'records':
            search_type = local_type(self.kwargs.get('search_type'))
            query = Search(search_type)
            filters = self.kwargs.get('filters', {})
            if not isinstance(filters, dict) or len(filters) > 16:
                raise ValueError('Use at most 16 exact field filters')
            columns = SearchType.get_column_info(search_type)
            for key, value in filters.items():
                if key not in columns or not isinstance(value, (str, int, float, bool)):
                    raise ValueError('Use existing fields with scalar filter values')
                query.add_filter(key, value)
            query.set_limit(50)
            self.info = dict(objects=[dict(item.get_data(), __search_key__=item.get_search_key(), revision=digest(item.get_data())) for item in query.get_sobjects()])
            return
        payload = {key: value for key, value in self.kwargs.items() if key not in ('operation_id', 'project_code')}
        if action=='upload':
            from tactic_stream.server.mcp_access import current_grant
            if not row['document']['allow_changes'] or row['status']!='running' and not current_grant(row):
                raise ValueError('This conversation does not authorize active changes')
            from .agent_attachment_cmd import AgentAttachmentCmd
            phase=self.kwargs.get('phase')
            if phase not in ('start','append','finish'):
                raise ValueError('Choose start, append or finish for an attachment upload')
            values={key:self.kwargs[key] for key in ('attachment_id','name','size','media_type','offset','data') if key in self.kwargs}
            command=AgentAttachmentCmd(action=phase,project_code=Project.get_project_code(),**values)
            Command.execute_cmd(command)
            if phase=='finish':
                metadata,_=attachment(values['attachment_id'])
                if not any(message.get('id')==metadata['attachment_id'] for message in row.get('messages',[])):
                    row.setdefault('messages',[]).append(dict(id=metadata['attachment_id'],role='user',text='',attachments=[metadata],delivered=True))
                    self.save('spt_agent_request',row['request_id'],row)
                self.info=metadata
            else:
                self.info=command.info
            return
        if action not in ('workflow_apply', 'checkin', 'link', 'create', 'patch', 'task_status'):
            raise ValueError('This agent operation is unavailable on the running server')
        operation_id = (str(uuid5(UUID(row['request_id']), json.dumps(payload, sort_keys=True)))
                        if action in ('link', 'task_status') else identity(self.kwargs.get('operation_id')))
        receipts = row.setdefault('operations', {})
        if operation_id in receipts and action != 'link':
            old = receipts[operation_id]
            if old['digest'] != digest(payload):
                raise ValueError('Operation ID already has different contents')
            if action == 'task_status':
                from tactic_stream.server.agent_tasks import verified_statuses
                self.info = verified_statuses(self.kwargs.get('changes'))
            else:
                self.info = old['result']
            return
        from tactic_stream.server.mcp_access import current_grant
        if not row['document']['allow_changes'] or row['status'] != 'running' and not current_grant(row):
            raise ValueError('This conversation does not authorize active changes')
        undo = None
        if action == 'task_status':
            from tactic_stream.server.agent_tasks import save_statuses
            result = save_statuses(self.kwargs.get('changes'))
        elif action == 'workflow_apply':
            reader = AgentActionsCmd(**dict(self.kwargs, action='workflow_read'))
            reader.execute()
            state = reader.info
            if self.kwargs.get('expected_revision') != state['revision']:
                raise ValueError('Project workflow or objects changed. Read again before applying.')
            search_type = state['search_type']
            pipeline_id = self.kwargs.get('identity', '')
            old = next((item for item in state['workflows'] if item['identity'] == pipeline_id), None)
            if pipeline_id and not old:
                raise ValueError('Choose a workflow returned by workflow_read')
            processes = self.kwargs.get('processes')
            if (not isinstance(processes, list) or not 1 <= len(processes) <= 50
                    or any(not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][\w .-]{0,79}', name) for name in processes)
                    or len(set(processes)) != len(processes)):
                raise ValueError('Use between 1 and 50 distinct process names')
            document = deepcopy(old['document']) if old else dict(name=self.kwargs.get('name', search_type), searchType=search_type)
            root = ET.fromstring(document.get('xml') or '<pipeline/>')
            previous = {node.get('name'): node for node in root.findall('process')}
            for node in list(root):
                if node.tag in ('process', 'connect'):
                    root.remove(node)
            for index, name in enumerate(processes):
                node = previous.get(name)
                if node is None:
                    node = ET.Element('process', name=name, type='manual', xpos=str(index * 180), ypos='100')
                root.append(node)
            for source, target in zip(processes, processes[1:]):
                ET.SubElement(root, 'connect', {'from': source, 'to': target})
            document['xml'] = ET.tostring(root, encoding='unicode')
            from tactic_client_lib import TacticServerStub
            server = TacticServerStub.get(protocol='local')
            if 'pipeline_code' not in state['columns']:
                server.add_column_to_search_type(search_type, 'pipeline_code', 'varchar(256)')
            result = json.loads(workflow_request('save', Project.get_project_code(), pipeline_id,
                                                document, old['revision'] if old else ''))
            keys = self.kwargs.get('search_keys', [])
            if not isinstance(keys, list) or not set(keys) <= set(row['document']['context']['search_keys']):
                raise ValueError('Workflow assignment must use captured selected objects')
            for key in keys:
                item = selected_object(key)
                if item.get_base_search_type() != search_type:
                    raise ValueError('Workflow assignment type mismatch')
                item.set_value('pipeline_code', result['identity'])
                item.commit()
            result = dict(identity=result['identity'], processes=processes, assigned=keys, revision=result['revision'])
        elif action == 'checkin':
            item = selected_object(self.kwargs.get('search_key'))
            local_type(item.get_base_search_type())
            process = text(self.kwargs.get('process'), 128)
            context = self.kwargs.get('context', '')
            if context:
                text(context, 256)
                if context != process and not context.startswith(process + '/'):
                    raise ValueError('Check-in context must belong to the chosen process')
            pipeline = Pipeline.get_by_code(item.get_value('pipeline_code', no_exception=True))
            if not pipeline or process not in pipeline.get_process_names():
                raise ValueError('Choose a process from the object workflow')
            codes = self.kwargs.get('attachments')
            allowed = {file['attachment_id'] for message in row.get('messages', []) for file in message.get('attachments', [])}
            if not isinstance(codes, list) or not codes or not set(codes) <= allowed:
                raise ValueError('Choose files attached to this conversation')
            from pyasm.checkin import FileCheckin
            from pyasm.common import Environment
            result = dict(snapshots=[])
            with tempfile.TemporaryDirectory(prefix='agent-checkin-', dir=Environment.get_upload_dir()) as staging:
                for code in codes:
                    metadata, source = attachment(code)
                    target = Path(staging) / metadata['name']
                    import shutil
                    shutil.copyfile(source, target)
                    paths, types = [str(target)], ['main']
                    from pyasm.biz import File, IconCreator
                    if File.get_extension(metadata['name']).lower() in File.IMAGE_EXT:
                        creator = IconCreator(str(target))
                        creator.execute()
                        for kind, path in (('web', creator.get_web_path()), ('icon', creator.get_icon_path())):
                            if path:
                                paths.append(path)
                                types.append(kind)
                    command = FileCheckin(item, paths, file_types=types, context=context or process + '/' + metadata['name'],
                                          process=process, description='Agent attachment: ' + metadata['name'],
                                          mode='create', source_paths=paths, keep_file_name=False)
                    command.get_transaction().set_sync(False)
                    Command.execute_cmd(command)
                    snapshot = command.get_snapshot()
                    result['snapshots'].append(snapshot.get_search_key())
        elif action == 'link':
            item = selected_object(self.kwargs.get('search_key'))
            local_type(item.get_base_search_type())
            search_type = local_type(self.kwargs.get('search_type') or row['document']['context']['search_type'])
            keys = self.kwargs.get('search_keys')
            if keys is None:
                keys = row['document']['context']['search_keys']
            if not isinstance(keys, list) or not 1 <= len(keys) <= 200 or len(set(keys)) != len(keys):
                raise ValueError('Choose between 1 and 200 distinct related objects')
            children = [selected_object(key) for key in keys]
            for child in children:
                if child.get_base_search_type() != search_type:
                    raise ValueError('Related object type mismatch')
            from tactic.command.sobject_link_cmd import SObjectLinkCmd
            command = SObjectLinkCmd(parent_key=item.get_search_key(), search_type=search_type,
                path=self.kwargs.get('path', ''), insert_search_keys=keys, exclude_search_keys=[])
            Command.execute_cmd(command)
            result = dict(command.info, parent=dict(search_key=item.get_search_key(), title=item.get_value('name', no_exception=True) or item.get_value('title', no_exception=True) or item.get_code()),
                linked_objects=[dict(search_key=child.get_search_key(), title=child.get_value('name', no_exception=True) or child.get_value('title', no_exception=True) or child.get_code()) for child in children])
        elif action == 'create':
            search_type = local_type(self.kwargs.get('search_type'))
            records = self.kwargs.get('records')
            columns = set(SearchType.get_column_info(search_type)) - {'id', 'project_code', 'timestamp', 's_status'}
            if not isinstance(records, list) or not 1 <= len(records) <= 50:
                raise ValueError('Create between 1 and 50 records')
            for values in records:
                if not isinstance(values, dict) or not set(values) <= columns:
                    raise ValueError('Create using existing ordinary entity fields')
                if any(value is not None and (type(value) not in (str, int, float, bool)
                        or isinstance(value, str) and len(value) > 12000) for value in values.values()):
                    raise ValueError('Record fields must be bounded scalar values')
            parent_key = self.kwargs.get('parent_key') or None
            if parent_key:
                parent = selected_object(parent_key)
                local_type(parent.get_base_search_type())
            from tactic_client_lib import TacticServerStub
            server = TacticServerStub.get(protocol='local')
            result = dict(objects=server.insert_multiple(search_type, records, parent_key=parent_key))
        elif action == 'patch':
            item = selected_object(self.kwargs.get('search_key'))
            local_type(item.get_base_search_type())
            before = item.get_data()
            if self.kwargs.get('expected_revision') != digest(before):
                raise ValueError('Object changed. Read it again before applying.')
            values = self.kwargs.get('values')
            allowed = set(SearchType.get_column_info(item.get_base_search_type())) - {'id', 'code', 'project_code', 'timestamp', 's_status', 'pipeline_code'}
            if not isinstance(values, dict) or not values or not set(values) <= allowed:
                raise ValueError('Patch only ordinary fields of the project entity')
            if any(value is not None and not isinstance(value, (str, int, float, bool)) for value in values.values()):
                raise ValueError('Field values must be scalar')
            for field, value in values.items():
                item.set_value(field, value, allow_none=True)
            item.commit()
            undo = dict(key=item.get_search_key(), before={field: before.get(field) for field in values}, after=values)
            result = dict(search_key=item.get_search_key(), revision=digest(item.get_data()))
        else:
            raise ValueError('Unknown agent editing operation')
        receipts[operation_id] = dict(digest=digest(payload), result=result, undo=undo)
        row['undo_operation'] = operation_id if undo else ''
        self.save('spt_agent_request', row['request_id'], row)
        self.info = result
