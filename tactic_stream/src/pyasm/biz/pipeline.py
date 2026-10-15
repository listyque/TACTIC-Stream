"""Pipeline, Process and ProcessConnect from pyasm/biz/pipeline.py.

Flat graph reads and administrator pipeline/process writes through native commands.
See LICENSE.TACTIC and compatibility/source_manifest.json.
"""
from pyasm.common.common import Base, Container
from pyasm.common.errors import UnsupportedContract
from pyasm.biz.prod_setting import ProjectSetting
from pyasm.biz.project import Project
from pyasm.search.search import Search, SearchType, SObject
from pyasm.search.sql import Sql
from pyasm.common.lxml_wrapper import Xml, XmlException


class PipelineException(Exception):
    pass



class Process(Base):

    def __init__(self, node):
        self.node = node
        self.parent_pipeline_code = None
        self.parent_pipeline = None
        self.child_pipeline = None
        self.is_sub_pipeline_process = False

    def __str__(self):
        return self.get_name()

    def get_node(self):
        return self.node

    def get_attributes(self):
        return Xml.get_attributes(self.node)

    def set_attribute(self, name, value):
        return Xml.set_attribute(self.node, name, value)

    def get_attribute(self, name):
        return Xml.get_attribute(self.node, name)

    def get_name(self):
        return Xml.get_attribute(self.node, 'name')

    def get_full_name(self):
        if self.parent_pipeline_code:
            return '%s/%s' % (self.parent_pipeline_code, self.get_name())
        else:
            return self.get_name()

    def get_type(self):
        node_type = Xml.get_attribute(self.node, 'type')
        if node_type == 'auto':
            node_type = 'action'
        if not node_type:
            node_type = 'manual'
        return node_type

    def get_group(self):
        return Xml.get_attribute(self.node, 'group')

    def get_color(self):
        color = Xml.get_attribute(self.node, 'color')
        return color

    def get_label(self):
        return Xml.get_attribute(self.node, 'label')

    def set_parent_pipeline_code(self, pipeline_code):
        """FIXME: a pipeline may have multi parents"""
        self.parent_pipeline_code = pipeline_code

    def set_parent_pipeline(self, pipeline):
        self.parent_pipeline = pipeline

    def set_sub_pipeline_process(self, is_sub_pipe):
        self.is_sub_pipeline_process = is_sub_pipe

    def is_from_sub_pipeline(self):
        return self.is_sub_pipeline_process

    def set_child_pipeline(self, pipeline):
        self.child_pipeline = pipeline

    def is_pipeline(self):
        return self.child_pipeline != None

    def get_parent_pipeline(self):
        return self.parent_pipeline

    def get_child_pipeline2(self):
        return self.child_pipeline

    def get_child_pipeline(self):
        return self.child_pipeline

    def get_task_pipeline(self, default=True):
        """ assuming the child pipeline is task related """
        task_pipeline_code = None
        process_name = self.get_name()
        try:
            search = Search('config/process')
        except LookupError as exc:
            if not str(exc).startswith('Unregistered SearchType:'):
                raise
            process = None
        else:
            search.add_filter('process', process_name)
            search.add_filter('pipeline_code', self.parent_pipeline_code)
            process = search.get_sobject()
        if process:
            workflow_data = process.get_json_value('workflow', {})
            version = workflow_data.get('version') or 1
            version_2 = version in [2, '2']
            properties = workflow_data.get('properties') or {}
            task_pipeline_code = properties.get('task_pipeline') if version_2 else workflow_data.get('task_pipeline')
            node_type = workflow_data.get('node_type')
        if not task_pipeline_code:
            task_pipeline_code = Xml.get_attribute(self.node, 'task_pipeline')
            node_type = Xml.get_attribute(self.node, 'type')
        if node_type == 'approval':
            return 'approval'
        elif node_type == 'dependency':
            return 'dependency'
        elif node_type == 'progress':
            return 'progress'
        if not task_pipeline_code and default:
            return 'task'
        else:
            return task_pipeline_code

    def get_completion(self):
        return Xml.get_attribute(self.node, 'completion')

    def get_handler(self):
        return Xml.get_attribute(self.node, 'handler')

    def get_action_nodes(self, scope='dependent'):
        action_nodes = []
        nodes = Xml.get_children(self.node)
        for node in nodes:
            node_name = Xml.get_node_name(node)
            if node_name == 'action':
                node_scope = Xml.get_attribute(node, 'scope')
                if scope and node_scope != scope:
                    continue
                action_nodes.append(node)
        return action_nodes

    def get_action_node(self, event_name, scope='dependent'):
        nodes = Xml.get_children(self.node)
        for node in nodes:
            node_name = Xml.get_node_name(node)
            if node_name == 'action':
                node_event = Xml.get_attribute(node, 'event')
                if node_event != event_name:
                    continue
                node_scope = Xml.get_attribute(node, 'scope')
                if scope and node_scope != scope:
                    continue
                return node

    def get_action_handler(self, event_name, scope='dependent'):
        action_node = self.get_action_node(event_name, scope=scope)
        if action_node is None:
            return None
        action_handler = Xml.get_attribute(action_node, 'class')
        return action_handler

    def get_action_options(self, event_name, scope='dependent'):
        options = {}
        action_node = self.get_action_node(event_name, scope=scope)
        if action_node is None:
            return options
        nodes = Xml.get_children(action_node)
        for node in nodes:
            name = Xml.get_node_name(node)
            if name == '#text':
                continue
            value = Xml.get_node_value(node)
            options[name] = value
        return options


class ProcessConnect(Base):

    def __init__(self, node):
        self.node = node

    def get_from_expression(self):
        return Xml.get_attribute(self.node, 'from_expression')

    def get_attr(self, name):
        return Xml.get_attribute(self.node, name)

    def get_to(self):
        return Xml.get_attribute(self.node, 'to')

    def get_from(self):
        return Xml.get_attribute(self.node, 'from')

    def get_name(self):
        return Xml.get_attribute(self.node, 'name')

    def get_title(self):
        return Xml.get_attribute(self.node, 'title')

    def get_to_attr(self):
        return Xml.get_attribute(self.node, 'to_attr') or 'input'

    def get_from_attr(self):
        return Xml.get_attribute(self.node, 'from_attr') or 'output'

    def get_to_pipeline(self):
        return Xml.get_attribute(self.node, 'to_pipeline')

    def get_from_pipeline(self):
        return Xml.get_attribute(self.node, 'from_pipeline')

    def get_to_expression(self):
        return Xml.get_attribute(self.node, 'to_expression')

    def get_context(self, from_xml=False):
        context = Xml.get_attribute(self.node, 'context')
        if from_xml:
            return context
        if not context:
            process = Xml.get_attribute(self.node, 'from')
            if process.find('/') != -1:
                parts = process.split('/')
                process = parts[1]
            context = process
        return context


class Pipeline(SObject):
    SEARCH_TYPE = 'sthpw/pipeline'

    def __init__(self, search_type='sthpw/pipeline', columns=None, result=None, fast_data=None):
        super(Pipeline, self).__init__(search_type, columns, result, fast_data=fast_data)
        self.processes = []
        self.recursive_processes = []
        self.connects = {}
        self.pipeline_dict = {}
        xml_str = self.get_value('pipeline', no_exception=True)
        if xml_str:
            self.set_pipeline(xml_str, cache=False)
        self.process_sobjects = None
        self.process_generation = None

    def set_pipeline(self, pipeline_xml, cache=True):
        if self.is_insert():
            cache = False
        search_key = self.get_search_key()
        xml_dict = Container.get('Pipeline:xml')
        if xml_dict is None:
            xml_dict = {}
            Container.put('Pipeline:xml', xml_dict)
        xml = xml_dict.get(search_key) if cache else None
        if xml is None:
            xml = Xml()
            pipeline_xml = pipeline_xml or '<pipeline/>'
            if '<!DOCTYPE' in pipeline_xml or '<!ENTITY' in pipeline_xml:
                raise UnsupportedContract('Pipeline DTD/entities are not supported')
            try:
                xml.read_string(pipeline_xml)
            except XmlException:
                xml.read_string('<pipeline/>')
        root = xml.get_root_node()
        nodes = Xml.get_children(root) if root.tag == 'pipeline' else []
        if any(node.tag == 'pipeline' for node in nodes):
            raise UnsupportedContract('Nested Pipeline graphs are not migrated')
        if cache and search_key not in xml_dict:
            xml_dict[search_key] = xml
        self.xml = xml
        self.processes, self.recursive_processes = [], []
        for node in nodes:
            if node.tag != 'process':
                continue
            process = Process(node)
            process.set_parent_pipeline_code(self.get_code())
            process.set_parent_pipeline(self)
            self.processes.append(process)

    def _get_connects(self, process='', direction='from'):
        process = str(process) if process else ''
        opposite = 'to' if direction == 'from' else 'from'
        connects = []
        for node in self.xml.get_nodes('pipeline/connect'):
            if process and Xml.get_attribute(node, direction) not in (str(process), '*'):
                continue
            opposite_name = Xml.get_attribute(node, opposite)
            full_name = '%s/%s' % (self.get_name(), opposite_name)
            if process == opposite_name or process == full_name:
                continue
            connects.append(ProcessConnect(node))
        return connects

    @classmethod
    def get_by_code(cls, code, allow_default=False):
        if not code:
            return None
        try:
            pipeline = Search.get_by_code('config/pipeline', code)
        except LookupError as exc:
            # A new owned database has no project configuration registry yet.
            if not str(exc).startswith('Unregistered SearchType:'):
                raise
            pipeline = None
        if not pipeline:
            pipeline = super().get_by_code(code)
        if not pipeline and code in ('task', 'approval', 'dependency', 'progress', 'milestone', 'snapshot'):
            from pyasm.biz.task import Task
            pipeline = SearchType.create('sthpw/pipeline')
            from pyasm.biz.prod_setting import ProjectSetting
            # The original stores the setting SObject instead of its value.
            task_code = ProjectSetting.get_value_by_key('task_pipeline') if code == 'task' else ''
            pipeline.set_value('code', task_code or code)
            templates = {'task': Task.get_default_task_xml, 'approval': Task.get_default_approval_xml,
                         'dependency': Task.get_default_dependency_xml, 'progress': Task.get_default_progress_xml,
                         'milestone': Task.get_default_milestone_xml, 'snapshot': Task.get_default_snapshot_xml}
            xml = templates[code]()
            pipeline.set_value('pipeline', xml)
            pipeline.set_pipeline(xml)
            pipeline.set_value('search_type', 'sthpw/' + (code if code in ('milestone', 'snapshot') else 'task'))
        if not pipeline and allow_default:
            search = Search(cls)
            search.add_filter('code', 'default')
            pipeline = search.get_sobject()
            if not pipeline:
                raise UnsupportedContract('Autogenerated default Pipeline requires SObject persistence')
        if pipeline and not pipeline.get_processes():
            pipeline.set_pipeline(pipeline.get_value('pipeline'))
        return pipeline

    def get_defaults(self):
        '''The default, if not specified is to set the current project'''
        defaults = {}

        project_code = Project.get_project_code()
        defaults['project_code'] = project_code

        from pyasm.search.transaction import Transaction
        transaction = Transaction.get()
        if transaction is None or not transaction.is_in_transaction():
            raise UnsupportedContract('Pipeline defaults require an active Command')
        if not self.get_value('code', no_exception=True):
            self.set_value('code', self.generate_code())
        self.update_dependencies()

        return defaults

    def update_dependencies(self):
        '''Function that should be run on insert/update. It's already automatically called during insert.
        On update, the caller needs to call this explicitly. It checks the search type
        this pipeline is associated with and if there is no pipeline code
        column, then update it.  It updates the process table also.'''

        if self.is_insert() and not hasattr(self, 'xml'):
            self.set_pipeline(self.get_value('pipeline'), cache=False)
        search_type = self.get_value('search_type')
        # Saved versions clone their owned definitions in SObject.clone.
        # Creating defaults here would leave duplicate, unbound processes.
        if not self.is_insert() or not self.get_value('parent_code', no_exception=True):
            self.update_process_table(search_type=search_type)

        # don't do anything for task sType
        if search_type =='sthpw/task':
            return


        if not search_type:
            return

        if ProjectSetting.get_value_by_key('autofill_pipeline_code') != 'false':
            if 'pipeline_code' not in SearchType.get_columns(search_type):
                from pyasm.command import ColumnAddCmd
                ColumnAddCmd(search_type, 'pipeline_code', 'varchar').execute()

            # go through all of the sobjects and set all the empty ones
            # to the new pipeline
            search = Search(search_type)
            search.add_op("begin")
            search.add_filter("pipeline_code", "NULL", op='is', quoted=False)
            search.add_filter("pipeline_code", "")
            search.add_op("or")
            for sobject in search.get_sobjects():
                sobject.set_value('pipeline_code', self.get_code())
                sobject.commit(triggers=False)

    def update_process_table(self, search_type=None):
        ''' make sure to update process table'''

        template = self.get_template_pipeline()
        if template:
            if template.get_code() == self.get_code():
                template_processes = []
            else:
                template_processes = template.get_process_names()
        else:
            template_processes = []


        process_names = self.get_process_names()
        pipeline_code = self.get_code()

        search = Search("config/process")
        search.add_filter("pipeline_code", pipeline_code)
        process_sobjs = search.get_sobjects()

        pipeline_has_updates = False
        count = 1
        for process_name in process_names:

            exists = False
            for process_sobj in process_sobjs:
                # if it already exist, then update
                if process_sobj.get_value("process") == process_name:
                    exists = True
                    break


            if not exists:
                process_sobj = SearchType.create("config/process")

                # default to (main) for non-task status pipeline
                if search_type and search_type != 'sthpw/task':
                    process_sobj.set_value('subcontext_options', '(main)')
                process_sobj.set_value("pipeline_code", pipeline_code)
                process_sobj.set_value("process", process_name)
                process_sobj.set_json_value("workflow", {"version": 2})


            # copy information over from the template
            if process_name in template_processes:
                template_attrs = template.get_process_attrs(process_name)
                process = self.get_process(process_name)
                for name, value in template_attrs.items():
                    if name in ['xpos', 'ypos', 'name', 'process_code']:
                        continue
                    process.set_attribute(name, value)
                    pipeline_has_updates = True



                search = Search("config/process")
                search.add_filter("process", process_name)
                search.add_filter("pipeline_code", template.get_code())

                # copy certain values from the template
                template_process = search.get_sobject()
                for name, value in (template_process.get_data() if template_process else {}).items():
                    if not value:
                        continue
                    if name in ['checkin_mode']:
                        process_sobj.set_value(name, value)



            attrs = self.get_process_attrs(process_name)
            color = attrs.get('color')
            if color:
                process_sobj.set_value("color", color)

            process_sobj.set_value("sort_order", count)
            process_sobj.commit()
            count += 1


        if pipeline_has_updates:
            self.set_value("pipeline", self.get_pipeline_xml().to_string())
            if not self.is_insert():
                self.commit()

        # Deletion is shared with direct SObject/XML-RPC deletes.
        names = set(process_names)
        for process_sobj in process_sobjs:
            if process_sobj.get_value('process') not in names:
                process_sobj.delete()

    def on_update(self):
        # The source looks up deleted nodes in the new graph and loses their type.
        # Keep it in the existing definition before a caller reloads the pipeline.
        if 'pipeline' not in self.prev_update_data:
            return
        previous = Xml()
        previous.read_string(self.prev_data.get('pipeline') or '<pipeline/>')
        old_types = {Xml.get_attribute(node, 'name'): Process(node).get_type()
                     for node in previous.get_nodes('pipeline/process')}
        new_types = {node.get_name(): node.get_type() for node in self.get_processes()}
        removed = set(old_types) - set(new_types)
        changed = {name for name in old_types.keys() & new_types.keys()
                   if old_types[name] != new_types[name]}
        if not removed and not changed:
            return
        search = Search('config/process')
        search.add_filter('pipeline_code', self.get_code())
        for definition in search.get_sobjects():
            name = definition.get_value('process')
            if name in removed:
                workflow = definition.get_json_value('workflow', {}) or {}
                workflow['node_type'] = old_types[name]
                definition.set_json_value('workflow', workflow)
                definition.commit(triggers='none')
            elif name in changed:
                self._delete_process_dependencies(definition, node_type=old_types[name])
                workflow = definition.get_json_value('workflow', {}) or {}
                definition.set_json_value('workflow', {
                    'version': workflow.get('version') or 2, 'node_type': new_types[name]})
                definition.set_value('subpipeline_code', 'NULL', quoted=False)
                definition.commit(triggers='none')

    @staticmethod
    def _delete_process_dependencies(definition, node_type=None):
        pipeline_code = definition.get_value('pipeline_code')
        process_name = definition.get_value('process')
        process_code = definition.get_code()
        workflow = definition.get_json_value('workflow', {}) or {}
        if node_type is None:
            pipeline = Pipeline.get_by_code(pipeline_code)
            node = pipeline.get_process(process_name) if pipeline else None
            node_type = node.get_type() if node else workflow.get('node_type')
        if node_type:
            from pyasm.command import CustomProcessConfig
            handler = CustomProcessConfig.get_delete_handler(node_type, {
                'pipeline_code': pipeline_code, 'process': process_name,
                'process_code': process_code, 'search_key': definition.get_search_key()})
            if handler:
                handler.execute()

        search = Search('config/trigger')
        search.add_filter('process', process_code)
        owned = {row.get_code(): row for row in search.get_sobjects()}
        # Progress listeners use the observed process name; their data owns them.
        progress = workflow.get('progress') or {}
        for code in (workflow.get('trigger_code'), progress.get('trigger_code')):
            if not code or code in owned:
                continue
            trigger = Search.get_by_code('config/trigger', code)
            data = trigger.get_json_value('data', {}) if trigger else {}
            if data.get('process_code') == process_code and data.get('pipeline_code') == pipeline_code:
                owned[code] = trigger
        if owned:
            for other in Search('config/process').get_sobjects():
                if other.get_code() == process_code:
                    continue
                settings = other.get_json_value('workflow', {}) or {}
                refs = (settings.get('trigger_code'), (settings.get('progress') or {}).get('trigger_code'))
                if any(code in owned for code in refs):
                    raise PipelineException('Process trigger is referenced by another process [%s]' % other.get_code())
            for trigger in owned.values():
                trigger.delete()

    def save_version(self):
        from tactic.command.python_cmd import check_script_execution
        from tactic.core.process_constants import TRIGGER_FOLDER_PREFIX
        from pyasm.search import DbContainer, Transaction
        check_script_execution()
        sql = DbContainer.get('sthpw')
        Transaction.get().register_database(sql)
        sql.lock_workflow_state()
        pipeline_code = self.get_code()

        # Original version sequence and recursive SObject clone.
        search = Search('sthpw/pipeline')
        search.add_filter('parent_code', pipeline_code)
        search.add_order_by('version desc')
        latest = search.get_sobject()
        version = (latest.get_value('version') or 0) if latest else 0
        new_pipeline = self.clone(related_types=['config/process'],
                                  extra_data={'version': version + 1, 'parent_code': pipeline_code})
        processes = self.get_related_sobjects('config/process')
        copies = {obj.get_value('process'): obj for obj in new_pipeline.get_related_sobjects('config/process')}
        process_codes = {obj.get_code(): copies[obj.get_value('process')].get_code() for obj in processes}
        trigger_codes, script_paths = {}, {}

        def references(value):
            # Remap configuration references, never source code or user strings.
            if isinstance(value, list):
                return [references(item) for item in value]
            if not isinstance(value, dict):
                return value
            result = {}
            for key, item in value.items():
                if key == 'process_code' and isinstance(item, str):
                    item = process_codes.get(item, item)
                elif key == 'trigger_code' and isinstance(item, str):
                    item = trigger_codes.get(item, item)
                elif key == 'script_path' and isinstance(item, str):
                    item = script_paths.get(item, item)
                elif key in ('pipeline_code', 'related_pipeline_code') and item == pipeline_code:
                    item = new_pipeline.get_code()
                result[key] = references(item)
            return result

        # Action triggers are keyed by process code; progress listeners keep
        # their related process name and refer to the owner in JSON data.
        search = Search('config/trigger')
        search.add_filters('process', list(process_codes))
        triggers = {obj.get_code(): obj for obj in search.get_sobjects()} if process_codes else {}
        for obj in processes:
            workflow = obj.get_json_value('workflow') or {}
            code = workflow.get('trigger_code') or (workflow.get('progress') or {}).get('trigger_code')
            if code and code not in triggers:
                trigger = Search.get_by_code('config/trigger', code)
                if trigger is None:
                    raise PipelineException('Missing process trigger [%s]' % code)
                triggers[code] = trigger

        trigger_copies = []
        for trigger in triggers.values():
            copied = trigger.clone()
            trigger_codes[trigger.get_code()] = copied.get_code()
            process_code = trigger.get_value('process')
            if process_code in process_codes:
                copied.set_value('process', process_codes[process_code])
            path = trigger.get_value('script_path')
            if path and path not in script_paths:
                folder, _, title = path.rpartition('/')
                search = Search('config/custom_script')
                search.add_filter('folder', folder)
                search.add_filter('title', title)
                script = search.get_sobject()
                if script is None:
                    raise PipelineException('Missing process script [%s]' % path)
                script_copy = script.clone(extra_data={'folder': TRIGGER_FOLDER_PREFIX + '/' + new_pipeline.get_code()})
                script_copy.set_value('title', script_copy.get_code())
                script_copy.commit()
                script_paths[path] = script_copy.get_value('folder') + '/' + script_copy.get_value('title')
            trigger_copies.append((trigger, copied))

        for original, copied in trigger_copies:
            copied.set_value('script_path', script_paths.get(original.get_value('script_path'), original.get_value('script_path')))
            data = original.get_json_value('data')
            if data:
                copied.set_json_value('data', references(data))
            copied.commit()
        for original in processes:
            copied = copies[original.get_value('process')]
            copied.set_json_value('workflow', references(original.get_json_value('workflow') or {}))
            copied.commit()
        xml = new_pipeline.get_pipeline_xml()
        for node in xml.get_nodes('pipeline/process'):
            copied = copies.get(Xml.get_attribute(node, 'name'))
            if copied:
                Xml.set_attribute(node, 'process_code', copied.get_code())
        new_pipeline.set_value('pipeline', xml.to_string())
        new_pipeline.commit()
        return new_pipeline

    @classmethod
    def set_to_latest(cls, sobject):
        pipeline = cls.get_by_sobject(sobject)
        if pipeline is None:
            raise PipelineException('Object has no pipeline')
        pipeline_code = pipeline.get_value('parent_code') or pipeline.get_code()
        search = Search('sthpw/pipeline')
        search.add_filter('parent_code', pipeline_code)
        search.add_order_by('version desc')
        latest = search.get_sobject()
        if latest:
            sobject.set_value('pipeline_code', latest.get_code())
            sobject.commit()

    @classmethod
    def set_to_versionless(cls, sobject):
        pipeline = cls.get_by_sobject(sobject)
        if pipeline is None:
            raise PipelineException('Object has no pipeline')
        parent_code = pipeline.get_value('parent_code')
        if parent_code:
            if cls.get_by_code(parent_code) is None:
                raise PipelineException('Missing versionless pipeline [%s]' % parent_code)
            sobject.set_value('pipeline_code', parent_code)
            sobject.commit()

    @staticmethod
    def create(name, desc, search_type, xml=None, code=None, color=None):
        '''will only create if it does not exist, otherwise it just updates'''

        if code:
            sobject = Pipeline.get_by_code(code)
        else:
            sobject = None

        if sobject == None:
            sobject = SearchType.create( Pipeline.SEARCH_TYPE )
        else:
            return sobject

        if not xml:
            xml = Xml()
            xml.create_doc('pipeline')

        if isinstance(xml, str):
            xml_string = xml
            xml = Xml()
            xml.read_string(xml_string)


        SearchType.get(search_type)
        sobject._check_business_write()
        sobject.set_value("pipeline", xml.get_xml())
        sobject.set_pipeline(xml.to_string())

        sobject.set_value('timestamp', Sql.get_default_timestamp_now(), quoted=False )
        if code:
            sobject.set_value('code', code.strip())
        sobject.set_value('name', name.strip())
        sobject.set_value('search_type', search_type)
        sobject.set_value('description', desc)

        if color:
            sobject.set_value("color", color)

        sobject.commit()



        return sobject

    @classmethod
    def get_template_pipeline(cls, search_type=None):
        search = Search("sthpw/pipeline")
        search.add_filter("name", "VFX Processes")
        pipeline = search.get_sobject()
        return pipeline

    def get_name(self, long=False):
        """this is the old function, kept for backward-compatibility"""
        return self.get_code()

    def get_pipeline_xml(self):
        return self.xml

    def to_string(self):
        return self.xml.to_string()

    def get_process(self, name):
        """returns a Process object"""
        if not isinstance(name, str):
            name = name.get_name()
        for process in self.processes:
            if process.get_name() == name:
                return process
        processes = self.get_processes(recurse=True)
        for process in processes:
            if process.get_full_name() == name:
                return process
        return None

    def get_processes(self, recurse=False, type=None):
        """returns all the Process objects in this pipeline"""
        if type and isinstance(type, str):
            types = [type]
        else:
            types = type
        if recurse:
            if self.recursive_processes:
                return self.recursive_processes
            else:
                for process in self.processes:
                    if types and process.get_type() not in types:
                        continue
                    self.recursive_processes.append(process)
                    child_pipeline = process.get_child_pipeline()
                    if not child_pipeline:
                        continue
                    child_processes = child_pipeline.get_processes(recurse=recurse)
                    for x in child_processes:
                        x.set_sub_pipeline_process(True)
                    self.recursive_processes.extend(child_processes)
                return self.recursive_processes
        elif types:
            ret_processes = []
            for process in self.processes:
                if process.get_type() not in types:
                    continue
                ret_processes.append(process)
            return ret_processes
        else:
            return self.processes

    def get_process_attrs(self, name):
        process = self.get_process(name)
        if process:
            return process.get_attributes()
        else:
            return {}

    def get_process_names(self, recurse=False, type=None, exclude=[]):
        """returns all the Process names in this pipeline"""
        if type and isinstance(type, str):
            types = type.split(',')
        else:
            types = type
        if exclude and isinstance(exclude, str):
            exclude = exclude.split(',')
        processes = self.get_processes(recurse, type=types)
        if recurse:
            process_names = []
            for process in processes:
                if types and process.get_type() not in types:
                    continue
                if exclude and process.get_type() in exclude:
                    continue
                if process.is_from_sub_pipeline():
                    process_names.append(process.get_full_name())
                else:
                    process_names.append(process.get_name())
            return process_names
        else:
            return [process.get_name() for process in processes if not exclude or process.get_type() not in exclude]

    def get_process_sobject(self, process):
        # search all processes and cache all of the sobject locally
        generation = Container.get('Pipeline:process_generation') or 0
        if self.process_sobjects is None or self.process_generation != generation:
            self.process_generation = generation

            try:
                project = self.get_value('project_code', no_exception=True) or self.get_project_code()
                search = Search("config/process?project=" + project)
            except LookupError as exc:
                if not str(exc).startswith('Unregistered SearchType:'):
                    raise
                self.process_sobjects = {}
                return None
            search.add_filter("pipeline_code", self.get_code())
            sobjects = search.get_sobjects()

            self.process_sobjects = {}

            for process_sobject in sobjects:
                # prevent changing variable process
                pcs = process_sobject.get("process")
                self.process_sobjects[pcs] = process_sobject


        process_sobject = self.process_sobjects.get(process)
        return process_sobject

    def get_process_sobjects(self):

        process_name = "dummy"

        self.get_process_sobject(process_name)

        return self.process_sobjects

    def get_index(self, name):
        index = 0
        for process in self.processes:
            if process.get_name() == name:
                return index
            index += 1

    def get_dependent_processes(self, start, end):
        process_names = self.get_process_names()
        if start not in process_names:
            print('process [%s] does not exist' % start)
            return
        if end not in process_names:
            print('process [%s] does not exist' % end)
            return
        process = end
        handled = []

        def handle_process(process, start):
            if process in handled:
                return
            handled.append(process)
            if process == start:
                return
            input_processes = self.get_input_processes(process, to_attr='input')
            if not input_processes:
                return
            for input_process in input_processes:
                input_process_name = input_process.get_name()
                handle_process(input_process_name, start)
        handle_process(process, start)
        return handled

    def get_input_processes(self, process, type=None, to_attr=None):
        connects = self._get_connects(process, direction='to')
        processes = []
        for connect in connects:
            if to_attr:
                connect_to_attr = connect.get_attr('to_attr')
                if not (to_attr == 'input' and (not connect_to_attr)):
                    if connect_to_attr != to_attr:
                        continue
            from_connect = connect.get_from()
            process = self.get_process(from_connect)
            if process:
                if type and process.get_type() != type:
                    continue
                processes.append(process)
        return processes

    def get_input_process_names(self, process, type=None, to_attr=None):
        input_processes = self.get_input_processes(process, type, to_attr)
        process_names = [x.get_name() for x in input_processes]
        return process_names

    def get_output_processes(self, process, type=None, from_attr=None):
        connects = self._get_connects(process, direction='from')
        if not connects:
            return []
        processes = []
        for connect in connects:
            to = connect.get_to()
            if from_attr:
                connect_from_attr = connect.get_attr('from_attr')
                if connect_from_attr != from_attr:
                    continue
            to_pipeline = connect.get_to_pipeline()
            if to_pipeline:
                pipeline = Pipeline.get_by_code(to_pipeline)
                process = pipeline.get_process(to)
                if type and process.get_type() != type:
                    continue
                if process:
                    processes.append(process)
            else:
                process = self.get_process(to)
                if process:
                    processes.append(process)
        return processes

    def get_output_process_names(self, process, type=None, from_attr=None):
        output_processes = self.get_output_processes(process, type, from_attr)
        process_names = [x.get_name() for x in output_processes]
        return process_names

    def get_output_contexts(self, process, show_process=False):
        connects = self._get_connects(process, direction='from')
        if not connects:
            if show_process:
                data = (None, process)
            else:
                data = process
            return [data]
        contexts = []
        for connect in connects:
            context = connect.get_context()
            if not context:
                context = connect.get_to()
            if show_process:
                data = (connect.get_to(), context)
            else:
                data = context
            contexts.append(data)
        return contexts

    def get_input_contexts(self, process, show_process=False):
        connects = self._get_connects(process, direction='to')
        contexts = []
        for connect in connects:
            context = connect.get_context()
            if not context:
                context = connect.get_from()
            if show_process:
                data = (connect.get_from(), context)
            else:
                data = context
            contexts.append(data)
        return contexts

    def get_group(self, process_name):
        process = self.get_process(process_name)
        return process.get_group()

    def get_input_connects(self, process):
        connects = self._get_connects(process, direction='to')
        if not connects:
            return []
        else:
            return connects

    def get_output_connects(self, process):
        connects = self._get_connects(process, direction='from')
        if not connects:
            return []
        else:
            return connects

    def get_input_streams(self, process):
        connects = self._get_connects(process, direction='to')
        if not connects:
            return []
        else:
            return [x.get_to_attr() for x in connects]

    def get_output_streams(self, process):
        connects = self._get_connects(process, direction='from')
        if not connects:
            return []
        else:
            return [x.get_from_attr() for x in connects]

    def get_forward_connects(self, process):
        connects = self._get_connects(process)
        process_names = []
        for connect in connects:
            process_names.append(connect.get_to())
        return process_names

    def get_backward_connects(self, process):
        connects = self._get_connects(process, direction='to')
        process_names = []
        for connect in connects:
            process_names.append(connect.get_from())
        return process_names

    def get_all_contexts(self):
        connects = self._get_connects()
        contexts = []
        for connect in connects:
            context = connect.get_context()
            if context not in contexts:
                contexts.append(context)
        return contexts

    @staticmethod
    def get_by_name(name):
        """ for backward-compatibility, name has been renamed as code """
        return Pipeline.get_by_code(name)

    @classmethod
    def get_by_search_type(cls, search_type, project_code=''):
        assert search_type
        search_type_obj = SearchType.get(search_type)
        if not search_type_obj:
            return []
        search_type = search_type_obj.get_base_key()
        cache_key = '%s|%s' % (search_type, project_code)
        search = Search('sthpw/pipeline')
        if search_type:
            search.add_filter('search_type', search_type)
        search.add_project_filter(project_code)
        pipelines = cls.get_by_search(search, cache_key, is_multi=True)
        if not pipelines:
            return []
        for pipe in pipelines:
            code = pipe.get_code()
            cls.cache_sobject('sthpw/pipeline|%s' % code, pipe)
        return pipelines

    @staticmethod
    def get_default():
        return Pipeline.get_by_code('default')

    @staticmethod
    def get_by_sobject(sobject, allow_default=False):
        """ get the pipeline of the sobject"""
        pipeline_name = ''
        if not sobject:
            return None
        if sobject.has_value('pipeline_code'):
            pipeline_name = sobject.get_value('pipeline_code')
        elif sobject.has_value('pipeline'):
            pipeline_name = sobject.get_value('pipeline')
        pipeline = Pipeline.get_by_code(pipeline_name, allow_default=allow_default)
        return pipeline

    @classmethod
    def create_pipeline_xml(cls, statuses, process_types=[], process_xpos=[], process_ypos=[]):
        """create regular pipeline with process_types, xpos, ypos or plain task status pipeline"""
        if not statuses:
            statuses = []
        xml = []
        xml.append('<pipeline>')
        if process_types:
            for i, status in enumerate(statuses):
                if status == '':
                    continue
                process_type = process_types[i]
                if len(process_xpos) > i:
                    xpos = process_xpos[i]
                else:
                    xpos = None
                if len(process_ypos) > i:
                    ypos = process_ypos[i]
                else:
                    ypos = None
                if xpos and ypos:
                    xml.append('  <process name="%s" type="%s" xpos="%s" ypos="%s"/>' % (status, process_type, xpos, ypos))
                else:
                    xml.append('  <process name="%s" type="%s"/>' % (status, process_type))
        else:
            for status in statuses:
                if status == '':
                    continue
                xml.append('  <process name="%s"/>' % status)
        last_status = None
        for i, status in enumerate(statuses):
            if status == '':
                continue
            if i == 0 or last_status == None:
                last_status = status
                continue
            xml.append('  <connect from="%s" to="%s"/>' % (last_status, status))
            last_status = status
        xml.append('</pipeline>')
        return '\n'.join(xml)


class ProjectPipeline(Pipeline):
    SEARCH_TYPE = 'config/pipeline'

    def get_defaults(self):
        defaults = {}

        self.update_dependencies()

        return defaults
