"""Project composition through native Commands, with durable non-atomic operation receipts."""
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID
import xml.etree.ElementTree as ET

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.config import config_file_lock
from pyasm.search import DbResource, Search, SearchType
from pyasm.security.security import _require_admin
from tactic.command.create_project_cmd import CreateProjectCmd
from tactic.command.project_template_cmd import ProjectTemplateCreatorCmd, ProjectTemplateInstallerCmd
from tactic_stream.project_plan import ProjectPlan


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def run(command):
    # Match Api.dispatch: remote sync is unsupported; local journaling/rollback stay enabled.
    command.get_transaction().set_sync(False)
    Command.execute_cmd(command)
    return command.get_info()


def available(code, title):
    CreateProjectCmd(project_code=code, project_title=title).check()
    query = Search('sthpw/search_object')
    query.add_filter('namespace', code)
    if query.get_sobject() or Search.get_by_code('sthpw/project_type', code, show_retired=True):
        raise ValueError('The project namespace already exists; choose another code')


def project_state(code):
    project = Search.get_by_code('sthpw/project', code, show_retired=True)
    resource = project.get_project_db_resource() if project else DbResource.get_default(code)
    exists = resource.get_database_impl().database_exists(resource)
    result = dict(project=code, registered=bool(project), database_exists=exists, retired=bool(project and project.is_retired()))
    if not project or not exists or result['retired']:
        return dict(result, revision=digest(result))
    previous = Project.get_project_code()
    try:
        Project.set_project(code)
        records = {'project': project.get_data()}
        for logical in ('sthpw/schema', 'sthpw/search_object', 'sthpw/pipeline', 'sthpw/login_group',
                        'sthpw/notification', 'config/widget_config', 'config/naming', 'config/process',
                        'config/trigger', 'config/custom_script', 'config/client_trigger', 'config/url', 'config/prod_setting'):
            query = Search(logical)
            query.set_show_retired(True)
            if logical == 'sthpw/schema':
                query.add_filter('code', code)
            elif logical == 'sthpw/search_object':
                query.add_filters('namespace', list({code, project.get_value('type')}))
            elif logical.startswith('sthpw/'):
                query.add_filter('project_code', code)
            query.add_order_by('id')
            records[logical] = [row.get_data() for row in query.get_sobjects()]
        for row in records['sthpw/search_object']:
            SearchType.clear_column_cache(row['search_type'])
        records['columns'] = {row['search_type']: SearchType.get_column_info(row['search_type'])
                              for row in records['sthpw/search_object']}
        sql = Search('config/widget_config').get_sql()
        records['generations'] = {table: sql.get_value("SELECT revision FROM %s WHERE code='collection'" % table)
                                  for table in ('spt_widget_config_revision', 'spt_naming_revision') if sql.table_exists(table)}
        from tactic_stream.server.navigation import read_navigation
        from tactic.ui.panel.naming_cmd import FIELDS
        result.update(revision=digest(records), entities=list(records['columns']),
                      pipelines=[row['code'] for row in records['sthpw/pipeline']],
                      columns=records['columns'], schema=[row['schema'] for row in records['sthpw/schema']],
                      workflows=[{key: row.get(key) for key in ('code', 'name', 'search_type', 'pipeline')}
                                 for row in records['sthpw/pipeline']],
                      naming=[{key: row.get(key) for key in FIELDS} for row in records['config/naming']],
                      navigation=read_navigation(), naming_rules=len(records['config/naming']))
        return result
    finally:
        Project.set_project(previous)


class ConfigureProjectCmd(Command):
    """Only a freshly created, empty project is eligible for this composition command."""

    def execute(self):
        from tactic.core.schema_commands import SearchTypeCreatorCmd
        from tactic.ui.panel.schema_cmd import SchemaCmd
        from tactic.ui.panel.workflow_cmd import WorkflowCmd
        from tactic.ui.panel.naming_cmd import NamingCmd
        from tactic.ui.panel.page_cmd import PageCmd
        _require_admin()
        plan = ProjectPlan.model_validate(self.kwargs['document'])
        code = plan.code
        if Project.get_project_code() != code:
            raise ValueError('Project composition context mismatch')
        types = Search('sthpw/search_object')
        types.add_filter('namespace', code)
        if types.get_sobject():
            raise ValueError('Composition only accepts an empty project; inspect partial state')
        pipeline_entities = {item.entity for item in plan.pipelines}
        for entity in plan.entities:
            creator = SearchTypeCreatorCmd(database=code, namespace=code, schema='public',
                search_type_name=entity.code, asset_title=entity.title, asset_description=entity.description,
                sobject_pipeline=entity.code in pipeline_entities)
            run(creator)
            from tactic_client_lib import TacticServerStub
            api = TacticServerStub.get(protocol='local')
            for column in entity.columns:
                api.add_column_to_search_type(code + '/' + entity.code, column.name, column.type)
        state = run(SchemaCmd(action='load', project_code=code))
        root = ET.fromstring(state['document']['xml'])
        create_columns, new_types = [], {}
        for relation in plan.relations:
            source, target = code + '/' + relation.source, code + '/' + relation.target
            if relation.instance:
                instance = code + '/' + relation.instance
                new_types[instance] = {}
                ET.SubElement(root, 'search_type', name=instance, type='instance')
                pairs = [(instance, source, relation.source_column), (instance, target, relation.target_column)]
            else:
                pairs = [(source, target, relation.source_column)]
            for child, parent, column in pairs:
                ET.SubElement(root, 'connect', {'from': child, 'to': parent, 'from_col': column,
                    'to_col': 'code', 'relationship': 'code'})
                create_columns.append({'from': child, 'to': parent, 'path': ''})
        run(SchemaCmd(action='save', project_code=code, expected_revision=state['revision'],
            document=dict(xml=ET.tostring(root, encoding='unicode'), createColumns=create_columns, newTypes=new_types)))
        for workflow in plan.pipelines:
            status_code = ''
            if workflow.statuses:
                graph = ET.Element('pipeline')
                for index, status in enumerate(workflow.statuses):
                    ET.SubElement(graph, 'process', name=status, type='status', xpos=str(index * 180), ypos='0')
                status_code = run(WorkflowCmd(action='save', project_code=code,
                    document=dict(name=workflow.entity + ' statuses', searchType='sthpw/task',
                                  xml=ET.tostring(graph, encoding='unicode'))))['identity']
            identity = code + '/' + workflow.entity
            state = run(WorkflowCmd(action='load', project_code=code, identity=identity))
            graph = ET.Element('pipeline')
            for index, process in enumerate(workflow.processes):
                node = ET.SubElement(graph, 'process', name=process, type='manual', xpos=str(index * 180), ypos='0')
                if status_code:
                    node.set('task_pipeline', status_code)
            for source, target in workflow.connections:
                ET.SubElement(graph, 'connect', {'from': source, 'to': target})
            run(WorkflowCmd(action='save', project_code=code, identity=identity, expected_revision=state['revision'],
                document=dict(name=workflow.entity, searchType=identity, xml=ET.tostring(graph, encoding='unicode'))))
        for rule in plan.naming:
            identity = code + '/' + rule.entity
            state = run(NamingCmd(action='load', project_code=code, search_type=identity))
            matching = [row for row in state['rules'] if row['document']['context'] == rule.context
                        and not row['document']['latest_versionless'] and not row['document']['current_versionless']]
            if len(matching) > 1:
                raise ValueError('Multiple native naming defaults match; inspect the new project')
            run(NamingCmd(action='save', project_code=code, search_type=identity, expected_revision=state['revision'],
                identity=matching[0]['identity'] if matching else '',
                document=dict(rule.model_dump(exclude={'entity'}), search_type=identity)))
        # Default pages use the same saved table/search/navigation owners as agent-authored pages.
        from uuid import uuid4
        for entity in plan.entities:
            identity = code + '/' + entity.code
            state = run(PageCmd(action='read', project_code=code, search_type=identity))
            run(PageCmd(action='apply', project_code=code, search_type=identity, expected_revision=state['revision'],
                operation_id=str(uuid4()), document=dict(name=entity.code, title=entity.title,
                    columns=[dict(name=name) for name in ['code', 'name', 'description'] + [c.name for c in entity.columns]])))
        self.info = project_state(code)


def project_agent_request(action, payload):
    """Each native command commits before its receipt advances; no encompassing transaction."""
    _require_admin()
    if action not in ('preview', 'create', 'read', 'export', 'install', 'operation'):
        raise ValueError('Unknown project agent operation')
    from pydantic import TypeAdapter
    from tactic_stream.project_plan import Code, Label
    code = TypeAdapter(Code).validate_python(payload.get('target'), strict=True)
    if code in ('admin', 'sthpw', 'prod'):
        raise ValueError('Choose a user project, not a system or excluded namespace')
    previous = Project.get_project_code()
    actor = Environment.get_user_name()
    root = Path(Environment.get_data_dir()) / 'agent_operations'
    key = digest([actor, previous, payload.get('operation_id')])
    path = root / (key + '.json')

    def read_receipt():
        return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None

    def write_receipt(receipt):
        temp = path.with_suffix('.tmp')
        with temp.open('w', encoding='utf-8') as output:
            json.dump(receipt, output, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)

    if action == 'read':
        return project_state(code)
    if action == 'preview':
        plan = ProjectPlan.model_validate(payload.get('document'))
        if plan.code != code:
            raise ValueError('Target must match project plan code')
        available(code, plan.title)
        config_types = Search('sthpw/search_object')
        config_types.add_filter('namespace', 'config')
        reserved = {item.get_table() for item in config_types.get_sobjects()}
        if reserved.intersection({item.code for item in plan.entities} | {edge.instance for edge in plan.relations}):
            raise ValueError('Entity names must not collide with native configuration tables')
        return dict(document=plan.model_dump(mode='json'), revision=digest(plan.model_dump()),
                    stages=['create database', 'configure native entities, schema, workflows, naming and pages'],
                    naming_preview='Structural validation only; verify paths with a real object before check-in',
                    atomic=False)
    operation_id = payload.get('operation_id')
    if not isinstance(operation_id, str) or str(UUID(operation_id)) != operation_id:
        raise ValueError('A canonical UUID operation_id is required')
    if action == 'operation':
        receipt = read_receipt()
        if not receipt:
            return dict(operation_id=operation_id, status='not_found', current=project_state(code))
        if receipt['target'] != code:
            raise ValueError('Operation belongs to another project')
        return dict(receipt, current=project_state(code))
    root.mkdir(parents=True, exist_ok=True)
    # Serialize cooperative provisioning/export writers, not ordinary administrator edits.
    with config_file_lock(root / 'projects'):
        fingerprint = digest({name: value for name, value in payload.items() if name != 'ticket'} | {'action': action})
        receipt = read_receipt()
        if receipt:
            if receipt['request_hash'] != fingerprint:
                raise ValueError('Operation ID was already used with a different request')
            if receipt['status'] != 'completed':
                raise ValueError('Operation is incomplete; inspect operation and current project state before manual recovery')
            return receipt
        if action == 'create':
            preview = project_agent_request('preview', payload)
            if preview['revision'] != payload.get('expected_revision'):
                raise ValueError('Project plan changed; preview it again')
        elif action == 'export':
            state = project_state(code)
            if not state['registered'] or not state['database_exists'] or state['retired'] or state['revision'] != payload.get('expected_revision'):
                raise ValueError('Project configuration changed; read it again before exporting')
        else:
            title = TypeAdapter(Label).validate_python(payload.get('title'), strict=True)
            available(code, title)
            template_id = str(UUID(payload.get('template_id', '')))
            source = root / (digest([actor, previous, template_id]) + '.json')
            template = json.loads(source.read_text(encoding='utf-8')) if source.is_file() else {}
            if template.get('status') != 'completed' or template.get('action') != 'export':
                raise ValueError('Select a completed export from this user and host project')
            artifact = Path(template['result']['path'])
            if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != template['result']['sha256']:
                raise ValueError('Template archive changed or is missing; export a new template')
        receipt = dict(operation_id=operation_id, target=code, action=action,
                       request_hash=fingerprint, status='started', stage=action)
        write_receipt(receipt)
        try:
            if action == 'create':
                plan = ProjectPlan.model_validate(payload['document'])
                run(CreateProjectCmd(project_code=code, project_title=plan.title, project_type=code,
                    description=plan.description, is_template=False))
                receipt['stage'] = 'configure'
                write_receipt(receipt)
                Project.set_project(code)
                result = run(ConfigureProjectCmd(document=plan.model_dump()))
            elif action == 'export':
                Project.set_project(code)
                # A unique native version prevents later exports overwriting this artifact.
                export = ProjectTemplateCreatorCmd(project_code=code, version=operation_id)
                run(export)
                artifact = Path(export.get_zip_path()).resolve()
                if project_state(code)['revision'] != state['revision']:
                    raise ValueError('Project changed during export; do not use this archive')
                result = dict(template_id=operation_id, path=artifact.as_posix(),
                              sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
                              bytes=artifact.stat().st_size, source_revision=state['revision'])
            else:
                run(ProjectTemplateInstallerCmd(path=str(artifact), project_code=code, project_title=title,
                    new_project=True, is_template=False))
                result = project_state(code)
            receipt.update(status='completed', result=result)
            write_receipt(receipt)
            return receipt
        except Exception:
            # Preserve the durable stage, including crash windows around native commits.
            receipt['status'] = 'needs_inspection'
            write_receipt(receipt)
            raise
        finally:
            Project.set_project(previous)
