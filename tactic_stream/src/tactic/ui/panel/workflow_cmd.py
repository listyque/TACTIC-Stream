"""Adopted from Handler thlib/ui/admin/workflow_api.py.

Workflow documents and the native process/trigger save lifecycle."""


def workflow_request(action: str, project_code: str, identity: str = '',
                     document: dict = None, expected_revision: str = '') -> str:
    import copy
    import hashlib
    import json
    import math
    import posixpath
    import xml.etree.ElementTree as ET
    from pyasm.biz import Pipeline, Project
    from tactic_client_lib import TacticServerStub
    from pyasm.security.security import _require_admin
    _require_admin()
    server = TacticServerStub.get(protocol='local')
    from pyasm.common.errors import SecurityException
    from pyasm.common import Environment
    from pyasm.search import Search, SearchType
    from tactic.ui.tools.pipeline_wdg import NewProcessInfoCmd

    if action == 'save':
        from pyasm.search import DbContainer
        sql = DbContainer.get('sthpw')
        # ponytail: pipeline registry lock; use per-pipeline locks if editing contention matters.
        sql.get_database_impl().lock_collection_table(sql, SearchType.get('sthpw/pipeline').get_table())
        Pipeline.clear_cache()

    if not Environment.get_security().is_admin():
        memberships = Search('sthpw/login_in_group')
        memberships.add_filter('login', server.get_login())
        if not any(group == 'admin' or 'supervisor' in group for group in (
                str(row.get_value('login_group') or '').lower()
                for row in memberships.get_sobjects())):
            raise SecurityException('TACTIC administrator or supervisor access is required')
    if not project_code or Project.get_project_code() != project_code:
        raise ValueError('Select a project before editing workflows')
    if action not in ('list', 'new', 'load', 'save'):
        raise ValueError('Unknown workflow operation')

    def catalog():
        query = Search('sthpw/pipeline')
        return sorted([
            {'identity': row.get_code(), 'label': row.get_value('name') or row.get_code(),
             'searchType': row.get_value('search_type') or '',
             'color': row.get_value('color') or '',
             'shared': not bool(row.get_value('project_code'))}
            for row in query.get_sobjects()
            if row.get_value('project_code') in (project_code, '', None)
        ], key=lambda row: (row['shared'], row['label']))

    def process_catalog(pipelines):
        if not pipelines:
            return []
        query = Search('config/process')
        query.add_filters('pipeline_code', [row['identity'] for row in pipelines])
        return sorted([
            {'identity': row.get_code(), 'label': row.get_value('process'),
             'pipeline': row.get_value('pipeline_code')}
            for row in query.get_sobjects()], key=lambda row: (row['pipeline'], row['label']))

    types = Project.get().get_search_types(
        include_multi_project=True, include_sthpw=True, include_config=True)
    # These are native engine node kinds, not translated project process names.
    kinds = ['manual', 'action', 'condition', 'approval', 'hierarchy',
             'dependency', 'progress', 'status']
    widgets = Search('config/widget_config')
    widgets.add_filter('category', 'workflow')
    for row in widgets.get_sobjects():
        name = row.get_value('view')
        if name and name not in kinds:
            kinds.append(name)
    pipelines = catalog()
    groups = Search('sthpw/login_group')
    logins = Search('sthpw/login')
    metadata = {'nodeTypes': kinds, 'searchTypes': [
        {'identity': row.get_code(), 'label': row.get_value('title') or row.get_code(),
         'color': row.get_value('color', no_exception=True) or ''}
        for row in types] + ([] if any(row.get_code() == 'sthpw/task' for row in types)
                            else [{'identity': 'sthpw/task', 'label': 'sthpw/task'}]),
        'pipelines': pipelines, 'processes': process_catalog(pipelines),
        'groups': sorted([
            {'identity': row.get_value('login_group'), 'label': row.get_value('login_group')}
            for row in groups.get_sobjects()], key=lambda row: row['label']),
        'users': sorted([
            {'identity': row.get_value('login'),
             'label': row.get_value('display_name') or row.get_value('login')}
            for row in logins.get_sobjects()], key=lambda row: row['label']),
        'canCreate': True}
    if action == 'list':
        return json.dumps({'catalog': pipelines, 'metadata': metadata, 'canWrite': True})
    if action == 'new':
        if identity not in {row['identity'] for row in metadata['searchTypes']}:
            raise ValueError('Choose a registered Search Type')
        # Prepare editor catalogs only; a pipeline is persisted by Save.
        return json.dumps({'identity': '', 'revision': '', 'document': {},
                           'catalog': pipelines, 'metadata': metadata, 'canWrite': True})
    if action == 'load' and not identity:
        if not pipelines:
            return json.dumps({'identity': '', 'revision': '', 'document': {},
                               'catalog': pipelines, 'metadata': metadata, 'canWrite': True})
        identity = pipelines[0]['identity']
    item = Pipeline.get_by_code(identity) if identity else None
    if identity and (not item or item.get_value('project_code') not in (project_code, '', None)):
        raise ValueError('This pipeline does not belong to the selected project')
    shared = bool(item and not item.get_value('project_code'))
    if shared and action == 'save':
        raise SecurityException('Shared pipelines are read-only here. Select a project-owned pipeline to edit.')
    metadata['shared'] = shared

    def processes():
        query = Search('config/process')
        query.add_filter('pipeline_code', identity)
        return query.get_sobjects() if identity else []

    def load_state():
        records = processes()
        if not item:
            return {}, [], records
        settings = {row.get_value('process'): row.get_json_value('workflow') or {}
                    for row in records}
        codes = [row.get_code() for row in records if row.get_code()]
        all_triggers = {}
        action_triggers_by_process = {}
        if codes:
            query = Search('config/trigger')
            query.add_filters('process', codes)
            for trig in query.get_sobjects():
                all_triggers[trig.get_code()] = trig.get_data()
                if trig.get_value('event') == 'process|action':
                    action_triggers_by_process.setdefault(trig.get_value('process'), trig)
        listeners = [(row.get_json_value('workflow') or {}).get('progress', {}).get('trigger_code')
                     for row in records]
        listeners = [code for code in listeners if code and code not in all_triggers]
        if listeners:
            query = Search('config/trigger')
            query.add_filters('code', listeners)
            all_triggers.update({row.get_code(): row.get_data() for row in query.get_sobjects()})
        script_keys = set()
        for trig in action_triggers_by_process.values():
            if not trig.get_value('class_name') and trig.get_value('script_path'):
                script_keys.add(posixpath.split(trig.get_value('script_path')))
        scripts_by_key = {}
        if script_keys:
            scripts = Search('config/custom_script')
            scripts.add_filters('folder', list({f for f, _ in script_keys}))
            scripts.add_filters('title', list({t for _, t in script_keys}))
            for s in scripts.get_sobjects():
                scripts_by_key[(s.get_value('folder') or '', s.get_value('title') or '')] = s
        # Native installations can keep action code only in custom_script,
        # rather than duplicating it in workflow JSON. Hydrate that source so
        # editing a description cannot accidentally disconnect its trigger.
        for row in records:
            trigger = action_triggers_by_process.get(row.get_code())
            if not trigger:
                continue
            defaults = settings[row.get_value('process')].setdefault('default', {})
            defaults['execute_mode'] = trigger.get_value('mode') or ''
            if trigger.get_value('class_name'):
                defaults.update(action='command', on_action_class=trigger.get_value('class_name'))
            elif trigger.get_value('script_path'):
                path = trigger.get_value('script_path')
                script = scripts_by_key.get(posixpath.split(path))
                defaults.update(action='create_new', script_path=path,
                                script=script.get_value('script') if script else '',
                                language=script.get_value('language') if script else 'python')
        descriptions = {row.get_value('process'): row.get_value('description') or ''
                        for row in records}
        doc = {'xml': item.get_value('pipeline') or '<pipeline/>',
               'name': item.get_value('name') or '',
               'description': item.get_value('description') or '',
               'color': item.get_value('color') or '',
               'searchType': item.get_value('search_type') or '',
               'processSettings': settings, 'processDescriptions': descriptions}
        return doc, list(all_triggers.values()), records

    current, triggers, process_records = load_state()

    def revision():
        owned_triggers = [row for row in triggers if row.get('event') == 'process|action'
                          or row.get('class_name') == 'pyasm.command.ProcessStatusTrigger']
        return hashlib.sha256(json.dumps([current, owned_triggers], sort_keys=True,
                                        default=str).encode()).hexdigest()

    if action == 'save':
        data = copy.deepcopy(document or {})
        if item and revision() != expected_revision:
            raise ValueError('Workflow or triggers changed on the server. Reload before saving.')
        search_type = str(data.get('searchType') or '')
        if not search_type:
            raise ValueError('Create a workflow from a saved Search Type.')
        if item and search_type != current['searchType']:
            raise ValueError('A pipeline belongs to its original Search Type. Create a workflow from the required Search Type instead.')
        if search_type not in {row.get_code() for row in types} | {'sthpw/task'}:
            raise ValueError('Select a Search Type from this project')
        xml = str(data.get('xml') or '')
        if '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():
            raise ValueError('Document types and XML entities are not supported')
        root = ET.fromstring(xml, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True)))
        if root.tag != 'pipeline':
            raise ValueError('The document must have a pipeline root')
        names = set()
        nodes = root.findall('process')
        if search_type == 'sthpw/task':
            for node in nodes:
                node.set('type', 'status')
            xml = ET.tostring(root, encoding='unicode')
        previous_processes = {
            node.get('name'): node
            for node in ET.fromstring(current.get('xml') or '<pipeline/>').findall('process')
        }
        previous_nodes = {name: node.get('type') or 'manual'
                          for name, node in previous_processes.items()}
        saved_codes = {node.get('process_code') for node in previous_processes.values()
                       if node.get('process_code')}
        for node in nodes:
            name = node.get('name', '').strip()
            if not name or name in names:
                raise ValueError('Process names must be non-empty and unique')
            names.add(name)
            # Guard edits to the XML value, not a possibly stale process table.
            previous = previous_processes.get(name)
            previous_code = previous.get('process_code') if previous is not None else None
            if node.get('process_code') != previous_code:
                if previous is None and node.get('process_code') in saved_codes:
                    raise ValueError('Saved process identifiers cannot be renamed. Change the display label instead.')
                raise ValueError('Process codes are generated by TACTIC and cannot be edited')
            kind = node.get('type') or 'manual'
            if kind not in kinds and kind != previous_nodes.get(name):
                raise ValueError('Select a node type installed on this server')
            for axis in ('xpos', 'ypos'):
                if not math.isfinite(float(node.get(axis, '0'))):
                    raise ValueError('Node positions must be finite')
        for edge in root.findall('connect'):
            if edge.get('from') not in names or edge.get('to') not in names:
                raise ValueError('Connection %s → %s refers to a missing process. Add the process or remove this connection before saving.'
                                 % (edge.get('from') or '?', edge.get('to') or '?'))
        changed = {}
        for node in nodes:
            name = node.get('name')
            settings = data.get('processSettings', {}).get(name, {})
            if not isinstance(settings, dict):
                raise ValueError('Process settings must be a JSON object')
            if any(key in settings and not isinstance(settings[key], dict)
                   for key in ('properties', 'default', 'hierarchy', 'progress')):
                raise ValueError('Process setting sections must be JSON objects')
            previous = current.get('processSettings', {}).get(name, {})
            properties = settings.get('properties') or {}
            old_properties = previous.get('properties') or {}
            for key in ('assigned_group', 'supervisor_group'):
                value = properties.get(key)
                if (value and value != old_properties.get(key)
                        and value not in {row['identity'] for row in metadata['groups']}):
                    raise ValueError('Choose an existing login group for %s' % key)
            task_pipeline = properties.get('task_pipeline')
            if (task_pipeline and task_pipeline != old_properties.get('task_pipeline')
                    and task_pipeline not in {row['identity'] for row in pipelines
                                              if row['searchType'] == 'sthpw/task'}):
                raise ValueError('Choose a task pipeline from this project or the shared catalog')
            description = data.get('processDescriptions', {}).get(name, '')
            previous_description = current.get('processDescriptions', {}).get(name, '')
            kind = node.get('type') or 'manual'
            if (settings != previous or description != previous_description
                    or kind != previous_nodes.get(name)):
                if settings.get('version', 2) != 2:
                    raise ValueError('This process uses an unsupported native workflow format')
                defaults = settings.get('default') or {}
                if (kind in ('action', 'condition') and defaults.get('script_path')
                        and defaults.get('action') != 'command' and not defaults.get('script')):
                    raise ValueError('The action script is empty or unavailable. Load its body or explicitly clear its path before saving.')
                changed[name] = dict(settings, process=name, pipeline_code=identity,
                                     node_type=kind,
                                     description=description, version=2)
        # Native update_dependencies removes config/process records for removed
        # nodes. Reject deletion/renaming while operational data still uses them.
        for process in process_records:
            name = process.get_value('process')
            if name in names:
                continue
            if any(row.get('process') == process.get_code() for row in triggers):
                raise ValueError('Process %s still has triggers; remove them in process dependencies first' % name)
            for logical in ('sthpw/task', 'sthpw/snapshot'):
                query = Search(logical)
                query.add_filter('project_code', project_code)
                query.add_filter('process', name)
                if current.get('searchType'):
                    query.add_filter('search_type', current['searchType'])
                query.set_limit(1)
                if query.get_sobject():
                    raise ValueError('Process %s is used by tasks or snapshots and cannot be removed' % name)
        if not item:
            item = SearchType.create('sthpw/pipeline')
            item.set_value('project_code', project_code)
        for key, field in (('name', 'name'), ('description', 'description'),
                           ('color', 'color'), ('searchType', 'search_type')):
            item.set_value(field, str(data.get(key) or ''))
        # The native model accepts valid XML directly. PipelineSaveCbk's web
        # pre-escaping is deliberately not applied to already escaped XML.
        item.set_value('pipeline', xml)
        item.commit()
        if not identity:
            identity = str(item.get_code() or '')
            if not identity:
                raise RuntimeError('TACTIC did not generate a pipeline code')
        # set_pipeline() only populates a cached in-memory XML graph. Persist
        # the field first, then reacquire the native owner with a fresh graph.
        Pipeline.clear_cache(search_key=item.get_search_key())
        item = Pipeline.get_by_code(identity)
        item.update_dependencies()
        codes = {row.get_value('process'): row.get_code() for row in processes()}
        for node in root.findall('process'):
            node.set('process_code', codes[node.get('name')])
        item.set_value('pipeline', ET.tostring(root, encoding='unicode'))
        item.commit()
        for kwargs in changed.values():
            kwargs['pipeline_code'] = identity
            NewProcessInfoCmd(**kwargs).execute()
        Pipeline.clear_cache(search_key=item.get_search_key())
        item = Pipeline.get_by_code(identity)
        current, triggers, process_records = load_state()
        metadata['pipelines'] = catalog()
        metadata['processes'] = process_catalog(metadata['pipelines'])
    if not item:
        raise ValueError('Select a pipeline')
    metadata['processCodes'] = {row.get_value('process'): row.get_code() for row in process_records}
    return json.dumps({'identity': identity, 'revision': revision(),
                       'canWrite': not shared and bool(current['searchType']),
                       'catalog': metadata['pipelines'], 'metadata': metadata,
                       'document': current}, default=str)


from pyasm.command import Command


class WorkflowCmd(Command):
    def execute(self):
        import json
        if self.kwargs.get('action') == 'layout':
            from pyasm.security.security import _require_admin
            from pyasm.biz import Project
            from .graph_document import GraphDocument
            from .graph_layout import layout_graph
            _require_admin()
            if self.kwargs.get('project_code') != Project.get_project_code():
                raise ValueError('Select a project before editing workflows')
            graph = GraphDocument('workflow', self.kwargs['document']['xml'])
            for position in layout_graph(graph.nodes(), graph.edges(), self.kwargs['style']):
                node = graph.node(position['identity'])
                node.set('xpos', str(position['nodeX']))
                node.set('ypos', str(position['nodeY']))
            return {'xml': graph.xml()}
        return json.loads(workflow_request(**self.kwargs))
