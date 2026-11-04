##########################################################
#
# Copyright (c) 2015, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#
from __future__ import print_function

__all__ = ['Workflow', 'WorkflowException', 'BaseWorkflowNodeHandler', 'BaseProcessTrigger', 'ProcessStatusTrigger', 'CustomProcessConfig', 'WorkflowManualNodeHandler']

from pyasm.common import Common, Config, jsondumps, jsonloads, TacticException, Container, Environment
from pyasm.command import Trigger, Command
from pyasm.common.errors import UnsupportedContract
from pyasm.search import SearchType, Search, SObject
from pyasm.biz import Pipeline, Task, Note

import six

'''
"node" and "manual" type nodes are synonymous, but the latter
is preferred as of 4.5
'''


PREDEFINED = [
        'pending',
        'in_progress',
        'action',
        'complete',
        'approved',
        'reject',
        'revise',
        'error',
        'not_required',
]


def _check_parent(sobject):
    from pyasm.common.errors import SecurityException
    if sobject is None or sobject.get_base_search_type().startswith(('sthpw/', 'config/')):
        raise SecurityException('Workflow requires an editable project object')
    sobject._check_business_write('edit')


def _commit_effect(effect, sobject):
    if Environment.get_security().is_admin():
        return effect.commit()
    _check_parent(sobject)
    previous = Container.get('Workflow:writing')
    Container.put('Workflow:writing', (effect, sobject))
    try:
        return effect.commit()
    finally:
        Container.put('Workflow:writing', previous)


def _check_effect(effect, access):
    from pyasm.common.errors import SecurityException
    scope = Container.get('Workflow:writing')
    if not scope or scope[0] is not effect:
        raise SecurityException('Workflow effects require their own transition')
    sobject = scope[1]
    _check_parent(sobject)
    base = effect.get_base_search_type()
    project = sobject.get_project_code()
    security = Environment.get_security()
    from pyasm.search.search import _context
    context = _context.get()
    if not security.is_logged_in() or security.get_user_name() != context.login:
        raise SecurityException('Workflow effects require the authenticated request identity')
    inserting = effect.get_id() in (-1, '-1', '')
    if access == 'delete' or (base in ('sthpw/message_log', 'sthpw/note') and not inserting and set(effect.update_data) != {'code'}):
        raise SecurityException('Workflow history only permits inserts and generated codes')
    if base in ('config/process_state', 'sthpw/note'):
        if base == 'config/process_state' and effect.get_project_code() != project:
            raise SecurityException('Workflow state belongs to another project database')
        parent = Search.get_by_search_key(sobject.get_search_key())
        if effect.get_value('search_type') != sobject.get_search_type():
            raise SecurityException('Workflow effect belongs to another parent type')
        if parent is None or parent.get_search_key() != sobject.get_search_key():
            raise SecurityException('Workflow effect belongs to another parent')
        if not effect.get_value('search_code', no_exception=True) and effect.get_value('search_id', no_exception=True) in (None, ''):
            raise SecurityException('Workflow effect requires a parent identity')
        for name, expected in (('search_code', sobject.get_code()), ('search_id', sobject.get_id())):
            if effect.get_value(name, no_exception=True) not in (None, '', expected):
                raise SecurityException('Workflow parent identities do not match')
    elif base in ('sthpw/message', 'sthpw/message_log'):
        key = effect.get_value('code' if base == 'sthpw/message' else 'message_code')
        source = Container.get('Workflow:message_source')
        if (source != (sobject, key) or not key.startswith(sobject.get_search_key() + '|') or
                not key.endswith(('|status', '|state'))):
            raise SecurityException('Workflow message requires its own parent and key')
    else:
        raise SecurityException('Unsupported Workflow effect')
    if base != 'config/process_state' and (effect.get_value('project_code') != project or effect.get_value('login') != context.login):
        raise SecurityException('Workflow effects must retain their project and authenticated author')
    if not inserting:
        current = Search(effect.get_search_type())
        current.add_id_filter(effect.get_id())
        current = current.get_sobject()
        if current is None:
            raise SecurityException('Workflow effect is outside the current read policy')
        for name in ('search_type', 'search_code', 'search_id', 'process', 'message_code', 'project_code'):
            if effect.get_value(name, no_exception=True) != current.get_value(name, no_exception=True):
                raise SecurityException('Workflow effect ownership cannot change')
        if base == 'config/process_state' and current.get_value('pipeline_code') and effect.get_value('pipeline_code') != current.get_value('pipeline_code'):
            raise SecurityException('Workflow state pipeline cannot change')
    for name in effect.update_data:
        if not security.check_access('sobject_column', {'search_type': base, 'column': name, 'project': project}, 'edit'):
            raise SecurityException('Workflow effect column is not editable: ' + name)
    return project


def _check_replay_effect(effect, access):
    from pyasm.common.errors import SecurityException
    scope = Container.get('Workflow:replay')
    node, parent = scope['node'], scope['parent']
    if effect.get_search_type() != node.get('search_type') or effect.get_code() != node.get('search_code'):
        raise SecurityException('Workflow replay permits only its current journal record')
    _check_parent(parent)
    security = Environment.get_security()
    from pyasm.search.search import _context
    if not security.is_logged_in() or security.get_user_name() != _context.get().login:
        raise SecurityException('Workflow replay requires the authenticated request identity')
    operation = access or ('insert' if effect.force_insert or effect.get_id() in (-1, '-1', '') else 'edit')
    if operation != scope['operation']:
        raise SecurityException('Workflow replay operation differs from its journal')
    project, base = parent.get_project_code(), effect.get_base_search_type()
    for name in scope['owners']:
        if str(effect.get_value(name, no_exception=True) or '') != str(scope['data'].get(name) or ''):
            raise SecurityException('Workflow replay ownership cannot change')
    if operation != 'insert':
        current = Search.get_by_id(effect.get_search_type(), effect.get_id())
        if current is None or current.get_code() != effect.get_code():
            raise SecurityException('Workflow replay record is missing or outside its read policy')
    keys = [{'code': base}, {'code': base, 'project': project}, {'code': '*'}, {'code': '*', 'project': project}]
    if (not security.check_access('search_type', keys, operation, default='allow') or
            not security.check_access('sobject', {'project': project, 'search_type': base, 'code': effect.get_code()}, operation, default='allow')):
        raise SecurityException('Workflow replay access denied')
    for name in effect.update_data if operation != 'delete' else ():
        if not security.check_access('sobject_column', {'search_type': base, 'column': name, 'project': project}, 'edit'):
            raise SecurityException('Workflow replay column is not editable: ' + name)
    return project


def _log_message(sobject, key, value):
    from pyasm.command import message
    previous = Container.get('Workflow:message_source')
    Container.put('Workflow:message_source', (sobject, key))
    try:
        return message.log_message(key, value)
    finally:
        Container.put('Workflow:message_source', previous)


def _check_workflow(input):
    """Preflight the migrated graph before callbacks or persistence."""
    pipeline = input.get("pipeline")
    if pipeline is None:
        return
    from tactic.command.python_cmd import check_script_execution
    if Environment.get_security().is_admin():
        check_script_execution()
    else:
        sobject = input.get('sobject')
        _check_parent(sobject)
        if (pipeline.get_value('project_code') not in (None, '', 'sthpw', sobject.get_project_code()) or
                pipeline.get_value('search_type') not in (None, '', sobject.get_base_search_type())):
            from pyasm.common.errors import SecurityException
            raise SecurityException('Workflow pipeline belongs to another project or search type')
    from pyasm.search import DbContainer, Transaction
    sql = DbContainer.get("sthpw")
    Transaction.get().register_database(sql)
    sql.lock_workflow_state()
    parents = input.get("parent_pipelines") or []
    if len(parents) != len(input.get("parent_processes") or []):
        raise ValueError("Workflow parent pipelines and processes must match")
    if pipeline.get_code() in [parent.get_code() for parent in parents]:
        raise ValueError("Recursive Workflow hierarchy: %s" % pipeline.get_code())
    # ponytail: repeat the small graph check at each event; cache only if
    # profiling large graphs shows this matters.
    definitions = pipeline.get_process_sobjects()
    Task._check_generation(pipeline, definitions)
    for process in pipeline.get_processes():
        if process.get_type() not in ("action", "manual", "node", "approval", "condition", "progress", "hierarchy", "input", "output", "dependency"):
            check_script_execution()
            config = CustomProcessConfig.get_config(process.get_type())
            name = config.get_display_handler('process') if config else None
            handler_class = Common.resolve_class(name) if name else None
            if not isinstance(handler_class, type) or not issubclass(handler_class, BaseWorkflowNodeHandler):
                raise UnsupportedContract("Workflow node type [%s] requires a registered backend handler" % process.get_type())
        if any(char in process.get_name() for char in (".", "/", "::")):
            raise UnsupportedContract("Hierarchical Workflow process names are not migrated")
        definition = definitions.get(process.get_name())
        if definition is None:
            raise TacticException("Process item [%s] has not been created." % process.get_name())
        if process.get_type() == "hierarchy":
            workflow = definition.get_json_value("workflow") or {}
            code = definition.get_value("subpipeline_code") or (workflow.get("default") or {}).get("subpipeline")
            if code:
                child = Pipeline.get_by_code(code)
            else:
                search = Search("sthpw/pipeline")
                search.add_filter("parent_process", definition.get_code())
                child = search.get_sobject()
            if not child or not child.get_processes():
                raise ValueError("Hierarchy process [%s] requires a nonempty subpipeline" % process.get_name())
            _check_workflow({"pipeline": child, "sobject": input.get('sobject'), "parent_pipelines": parents + [pipeline],
                             "parent_processes": (input.get("parent_processes") or []) + [process.get_name()]})


class WorkflowException(Exception):
    pass



class Workflow(object):
    startup_initialized = False

    def init(self, startup=False, quiet=False):

        key = "Workflow::is_initialized"
        is_initialized = Container.get(key)
        if self.startup_initialized or (not startup and is_initialized == "true"):
            return

        if not quiet:
            print("Initializing Workflow Engine")

        # initialize the triggers for the workflow
        event = "process|pending"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event, temp=True)
        trigger.set_value("class_name", ProcessPendingTrigger, temp=True)
        trigger.set_value("mode", "same process,same transaction", temp=True)
        Trigger.append_static_trigger(trigger, startup=startup)

        event = "process|action"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event, temp=True)
        trigger.set_value("class_name", ProcessActionTrigger, temp=True)
        trigger.set_value("mode", "same process,same transaction", temp=True)
        Trigger.append_static_trigger(trigger, startup=startup)


        event = "process|complete"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event, temp=True)
        trigger.set_value("class_name", ProcessCompleteTrigger, temp=True)
        trigger.set_value("mode", "same process,same transaction", temp=True)
        Trigger.append_static_trigger(trigger, startup=startup)

        event = "process|approved"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event, temp=True)
        trigger.set_value("class_name", ProcessApproveTrigger, temp=True)
        trigger.set_value("mode", "same process,same transaction", temp=True)
        Trigger.append_static_trigger(trigger, startup=startup)


        event = "process|not_required"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event, temp=True)
        trigger.set_value("class_name", ProcessNotRequiredTrigger, temp=True)
        trigger.set_value("mode", "same process,same transaction", temp=True)
        Trigger.append_static_trigger(trigger, startup=startup)



        event = "process|reject"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event, temp=True)
        trigger.set_value("class_name", ProcessRejectTrigger, temp=True)
        trigger.set_value("mode", "same process,same transaction", temp=True)
        Trigger.append_static_trigger(trigger, startup=startup)

        event = "process|revise"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event, temp=True)
        trigger.set_value("class_name", ProcessReviseTrigger, temp=True)
        trigger.set_value("mode", "same process,same transaction", temp=True)
        Trigger.append_static_trigger(trigger, startup=startup)

        event = "process|error"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event, temp=True)
        trigger.set_value("class_name", ProcessErrorTrigger, temp=True)
        trigger.set_value("mode", "same process,same transaction", temp=True)
        Trigger.append_static_trigger(trigger, startup=startup)


        event = "process|custom"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event, temp=True)
        trigger.set_value("class_name", ProcessCustomTrigger, temp=True)
        trigger.set_value("mode", "same process,same transaction", temp=True)
        Trigger.append_static_trigger(trigger, startup=startup)



        event = "workflow|listen"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event, temp=True)
        trigger.set_value("class_name", ProcessListenTrigger, temp=True)
        trigger.set_value("mode", "same process,same transaction", temp=True)
        Trigger.append_static_trigger(trigger, startup=startup)

        """
        class TestCmd(Command):
            def execute(self):
                Trigger.call(self, "workflow|listen")
        cmd = TestCmd()
        Command.execute_cmd(cmd)
        """






        # by default a stataus change to a trigger calls the node's trigger
        event = "change|sthpw/task|status"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event, temp=True)
        trigger.set_value("class_name", TaskStatusChangeTrigger, temp=True)
        trigger.set_value("mode", "same process,same transaction", temp=True)
        Trigger.append_static_trigger(trigger, startup=startup)


        Container.put(key, "true")
        if startup:
            Workflow.startup_initialized = True



class TaskStatusChangeTrigger(Trigger):

    def execute(self):

        """
        key = "enable_workflow_engine"
        from prod_setting import ProdSetting
        setting = ProdSetting.get_value_by_key(key)
        if setting not in [True, 'true']:
            return
        """


        # this prevents status trigger from running twice due to the workflow engine changing
        # the status of all the tasks in a process.
        is_internal = Container.get("TaskStatusChangeTrigger::internal")
        if is_internal:
            return



        # find the node in the pipeline
        task = self.get_caller()
        sobject = task.get_parent()
        if not sobject:
            return

        pipeline = None
        process_name = task.get_value("process")
        if "::" in process_name:
            pipeline_code, process_name = process_name.split("::", 1)
            pipeline = Pipeline.get_by_code(pipeline_code)
            if pipeline is None:
                raise LookupError("Task workflow pipeline no longer exists")

        if not pipeline and any(char in process_name for char in ("/", ".")):
            pipeline = Pipeline.get_by_sobject(sobject)

        process_code = task.get_value("process_code", no_exception=True)
        if process_code and not pipeline:
            process_sobj = Search.get_by_code("config/process", process_code)
            if process_sobj:
                pipeline_code = process_sobj.get_value("pipeline_code")
                pipeline = Pipeline.get_by_code(pipeline_code)

        if not pipeline:
            pipeline = Pipeline.get_by_sobject(sobject)

        if not pipeline:
            return


        if pipeline.get_value("use_workflow", no_exception=True) in [False, "false"]:
            return


        _check_workflow({"pipeline": pipeline, "sobject": sobject})
        status = task.get_value("status")
        if status.lower().replace(" ", "_") in PREDEFINED:
            status = status.lower().replace(" ", "_")

        # handle the approve case (which really means complete)
        if status in ["approved", "not_required"]:
            status = "complete"
        elif status == "in_progress":
            status = "action"



        # The task may have a hierarchy in it.  This is denoted by a / (or .) delimiter.
        # Both are supported for now, however, it is possible people will use a "/"
        # in the process name.
        parent_pipelines = []
        parent_processes = []
        parts = None
        if process_name.find(".") != -1:
            parts = process_name.split(".")

        elif process_name.find("/") != -1:
            parts = process_name.split("/")

        if parts:
            for part in parts[:-1]:
                process_name = part
                process = pipeline.get_process(process_name)


                if process:

                    # find the pipeline
                    search = Search("config/process")
                    search.add_filter("pipeline_code", pipeline.get_code())
                    search.add_filter("process", process_name)
                    process_sobj = search.get_sobject()

                    parent_pipeline = pipeline
                    parent_pipelines.append(pipeline)
                    parent_process = process_name
                    parent_processes.append(process_name)

                    # find the current process and pipeline_code
                    workflow = process_sobj.get_json_value("workflow") or {}
                    pipeline_code = process_sobj.get_value("subpipeline_code") or (workflow.get("default") or {}).get("subpipeline")
                    if pipeline_code:
                        pipeline = Pipeline.get_by_code(pipeline_code)
                    else:
                        search = Search("sthpw/pipeline")
                        search.add_filter("parent_process", process_sobj.get_code())
                        pipeline = search.get_sobject()
                    if not pipeline:
                        raise ValueError("Hierarchy task requires a subpipeline")

                    process = pipeline.get_process(parts[-1])


        else:
            process = pipeline.get_process(process_name)

        if not process:
            # we don't have enough info here
            return

        node_type = process.get_type()
        process_name = process.get_name()

        # need to clear message entry
        key = "%s|%s|status" % (sobject.get_search_key(), task.get_value("process"))
        from pyasm.command import message as server
        _log_message(sobject, key, "")


        if status in PREDEFINED:
            event = "process|%s" % status
        else:
            event = "process|custom"

        output = {
            'sobject': sobject,
            'pipeline': pipeline,
            'parent_pipelines': parent_pipelines,
            'process': process_name,
            'parent_processes': parent_processes,
            'status': status,
            'internal': True,
            'task': task,
        }
        # Task changes arrive in a new request; retain the node's saved input.
        state_key = "%s|%s|state" % (sobject.get_search_key(), task.get_value("process"))
        state = server.get_message(state_key).get('message')
        if state:
            state = jsonloads(state)
            output['data'] = state.get('data')
            output['packages'] = state.get('packages')
        Trigger.call(task, event, output=output)




class ProcessStatusTrigger(Trigger):

    def execute(self):
        process = self.input.get("process")
        pipeline_code = self.input.get("pipeline")
        status = self.input.get("status")
        sobject = self.input.get("sobject")

        pipeline = pipeline_code if isinstance(pipeline_code, Pipeline) else Pipeline.get_by_code(pipeline_code)
        _check_workflow(dict(self.input, pipeline=pipeline))

        # related process
        trigger_sobj = self.get_trigger_sobj()
        data = trigger_sobj.get_json_value("data")
        related_process_code = data.get("process_code")
        related_type = data.get("search_type")
        related_pipeline_code = data.get("pipeline_code")

        related_pipeline = Pipeline.get_by_code(related_pipeline_code)

        related_process_sobj = Search.get_by_code("config/process", related_process_code)
        if related_process_sobj is None or related_pipeline is None or related_process_sobj.get_value('pipeline_code') != related_pipeline_code:
            raise LookupError('Progress listener requires an existing process in its pipeline')
        related_process = related_process_sobj.get_value("process")


        # get the related sobject
        related_sobjects = Search.eval("@SOBJECT(%s)" % related_type, sobjects=[sobject])

        for related_sobject in related_sobjects:

            if SearchType.column_exists(related_sobject.get_search_type(), 'pipeline_code') and related_sobject.get_value('pipeline_code') != related_pipeline_code:
                continue

            # inputs are reversed
            kwargs = {
                'sobject': related_sobject,
                'process': related_process,
                'pipeline': related_pipeline,
                'status': status,
                'related_sobject': sobject,
                'related_pipeline': pipeline,
                'related_process': process,
                'data': self.input.get('data'),
                'packages': self.input.get('packages'),
            }



            normalized = status.lower().replace(' ', '_')
            event = 'process|action' if normalized == 'in_progress' else 'process|' + normalized if normalized in PREDEFINED else 'process|custom'
            _check_workflow(kwargs)
            Trigger.call(self, event, kwargs)




#
# Packaging
#

class BaseWorkflowPackage(object):

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.sobject = kwargs.get("sobject")

    def get_package(self):

        package = {}
        return {}


#
# Built in process triggers
#


class BaseProcessTrigger(Trigger):

    def get_handler(self, node_type):

        if node_type == "action":
            handler = WorkflowActionNodeHandler(input=self.input)
        elif node_type == "approval":
            handler = WorkflowApprovalNodeHandler(input=self.input)
        elif node_type in ["manual", "node"]:
            handler = WorkflowManualNodeHandler(input=self.input)
        elif node_type == "hierarchy":
            handler = WorkflowHierarchyNodeHandler(input=self.input)
        elif node_type == "input":
            handler = WorkflowInputNodeHandler(input=self.input)
        elif node_type == "output":
            handler = WorkflowOutputNodeHandler(input=self.input)
        elif node_type == "condition":
            handler = WorkflowConditionNodeHandler(input=self.input)
        elif node_type == "dependency":
            handler = WorkflowDependencyNodeHandler(input=self.input)
        elif node_type == "progress":
            handler = WorkflowProgressNodeHandler(input=self.input)

        elif node_type:
            extra_options = {
                    'input': self.input
            }
            handler = CustomProcessConfig.get_process_handler(node_type, extra_options)
        return handler



    def get_full_process_name(self, process):
        if "::" in process:
            return process
        parents = (self.input or {}).get("parent_processes") or []
        if process.find("/") == -1 and parents:
            full_process_name = "%s/%s" % ("/".join(parents), process)
        else:
            full_process_name = process

        input = self.input or {}
        pipeline = (input.get('parent_pipelines') or [input.get('pipeline')])[0]
        sobject = input.get('sobject')
        primary_code = sobject.get_value('pipeline_code', no_exception=True) if sobject else ''
        if pipeline and primary_code and pipeline.get_code() != primary_code:
            full_process_name = '%s::%s' % (pipeline.get_code(), full_process_name)
        return full_process_name


    def get_process_sobj(self, pipeline=None, process=None):
        if not process:
            process = self.process
        if not pipeline:
            pipeline = self.pipeline

        return pipeline.get_process_sobject(process)



    def set_all_tasks(self, sobject, process, status):

        full_process_name = self.get_full_process_name(process)
        tasks = Task.get_by_sobject(sobject, process=full_process_name)

        # prevent TaskStatusChangeTrigger from setting a custom task status back to complete
        if not hasattr(self, "internal"):
            self.internal = self.input.get("internal") or False

        if self.internal:
            return tasks

        title = status.replace("-", " ")
        title = title.replace("_", " ")
        title = Common.get_display_title(title)

        # this will force TaskStatusChangeTrigger to ignore execution
        previous = Container.get("TaskStatusChangeTrigger::internal")
        Container.set("TaskStatusChangeTrigger::internal", True)
        try:
            for task in tasks:
                task.set_value("status", title)
                task.commit()
        finally:
            Container.set("TaskStatusChangeTrigger::internal", previous)

        return tasks



    def run_callback(self, pipeline, process, status):

        parts = []
        if process.find(".") != -1:
            parts = process.split(".")
        if process.find("/") != -1:
            parts = process.split("/")

        if parts:
            subpipeline = parts[0]
            process = parts[-1]




        # get the node triggers
        process_sobj = self.get_process_sobj(pipeline, process)

        #print("callback process: ", process, pipeline.get_code())
        if not process_sobj:
            raise TacticException('Process item [%s] has not been created.'%process)



        triggers = {}
        if process_sobj:
            triggers = process_sobj.get_json_value("workflow")
        if not triggers:
            triggers = {}

        ret_val = None

        action = triggers.get("on_%s" % status)
        js_action = triggers.get("cbjs_%s" % status)
        action_path = triggers.get("on_%s_path" % status)

        kwargs, input = self.build_trigger_input()
        if action or action_path:
            from tactic.command import PythonCmd
            if action:
                cmd = PythonCmd(code=action, input=input, **kwargs)
            else:
                cmd = PythonCmd(script_path=action_path, input=input, **kwargs)

            ret_val = cmd.execute()

        elif js_action:
            raise UnsupportedContract("Server JavaScript callbacks are not migrated")
        else:
            # or call a trigger
            event = "process|%s" % status

            process_code = process_sobj.get_code()
            triggers = Trigger.call(self, event, kwargs, process=process_code)
            if triggers:
                try:
                    ret_val = triggers[0].get_ret_val()
                except Exception as e:
                    print("WARNING: ", e)
                    ret_val = ""



        return ret_val



    def build_trigger_input(self):
        # create a package for the trigger

        pipeline = self.input.get("pipeline")
        process = self.input.get("process")
        sobject = self.input.get("sobject")
        status = self.input.get("status")
        data = self.input.get("data")
        packages = self.input.get("packages")



        kwargs = {
            'sobject': sobject,
            'pipeline': pipeline,
            'process': process,
            'status': status,
            'data': data
        }
        input = {
            'sobject': sobject.get_sobject_dict(),
            'pipeline': pipeline.to_string(),
            'process': process,
            'status': status,
            'inputs': [x.get_name() for x in pipeline.get_input_processes(process)],
            'outputs': [x.get_name() for x in pipeline.get_output_processes(process)],
            'data': data,
            'packages': packages,
        }
        return kwargs, input



    def notify_listeners(self, sobject, process, status):

        # find all of the nodes that are listening to this status
        raise UnsupportedContract("BaseProcessTrigger.notify_listeners requires the remaining Workflow handlers")
        event = "%s|%s|%s" % (sobject.get_search_key(), process, status)
        #Trigger.call(self, event, self.input)

        # or

        search = Search("sthpw/process")
        search.add_filter("type", "listen")
        search.add_filter("key", event)
        process_sobjs = search.get_sobjects()

        # we have all of the processes that are listening

        for process_sobj in process_sobjs:

            # for each process, we need to find the related sobjects


            # so what exactly does this do ...
            # shouldn't this use triggers?
            pipeline_code = process_sobj.get_value("pipeline_code")
            pipeline = Pipeline.get_by_code(pipeline_code)

            # find all of the related sobjects
            process_obj = pipeline.get_process(process)
            related_search_type = process_obj.get_attribute("search_type")
            related_status = process_obj.get_attribute("status")
            related_process = process_obj.get_attribute("process")
            related_scope = process_obj.get_attribute("scope")

            # get the node's triggers
            if not related_search_type:
                search = Search("config/process")
                search.add_filter("process", self.process)
                search.add_filter("pipeline_code", pipeline.get_code())
                process_sobj = search.get_sobject()

                workflow = process_sobj.get_json_value("workflow", {})
                related_search_type = workflow.get("search_type")
                related_proces = workflow.get("proces")
                related_status = workflow.get("status")
                related_scope = workflow.get("scope")







    def check_complete_inputs(self):
        # this checks all the dependent inputs to determine whether they are complete.

        pipeline = self.input.get("pipeline")
        process = self.input.get("process")
        sobject = self.input.get("sobject")

        # Reject checks dependency completion without completing its pipeline.
        if self.input.get("dependency_run"):
            return True


        caller_sobject = self.input.get("related_sobject")
        if not caller_sobject:
            return True


        related_pipeline = self.input.get("related_pipeline")
        related_process = self.input.get("related_process")
        related_search_type = caller_sobject.get_base_search_type()


        # find related sobjects
        search = Search(related_search_type)
        if related_pipeline:
            search.add_filter("pipeline_code", related_pipeline.get_value("code"))

        search.add_relationship_filter(sobject)
        related_sobjects = search.get_sobjects()

        #related_sobjects = sobject.get_related_sobjects(related_search_type)
        #related_sobjects = Search.eval("@SOBJECT(%s)" % related_search_type, sobject)
        if not related_sobjects:
            return True

        # get the message status from each of these
        keys = []
        for related_sobject in related_sobjects:
            # ignore the caller as we know that is complete
            if related_sobject.get_search_key() == caller_sobject.get_search_key():
                continue

            key = "%s|%s|status" % (related_sobject.get_search_key(), related_process)
            keys.append(key)

        # get the statuses
        search = Search("sthpw/message")
        search.add_filters("code", keys)
        message_sobjects = search.get_sobjects()


        complete = {}

        # find the status
        for message_sobject in message_sobjects:
            status = message_sobject.get_value("message")
            if status in ["complete"]:
                complete[message_sobject.get_code()] = True


        # some backwards compatibility to figure out if the related sobject is "complete"
        if False and len(message_sobjects) < len(keys):
            # look at the overall status
            for related_sobject in related_sobjects:
                key = "%s|%s|status" % (related_sobject.get_search_key(), related_process)
                overall_status = related_sobject.get_value("status", no_exception=True)
                if overall_status.lower() == "complete":
                    complete[key] = True

                else:
                    related_tasks = Search.eval("@SOBJECT(sthpw/task['process','%s'])" % related_process, related_sobject)
                    for related_task in related_tasks:
                        related_status = related_task.get_value("status")
                        if related_status.lower() == "complete":
                            complete[key] = True


        # the caller is implied to be complete
        key = "%s|%s|status" % (caller_sobject.get_search_key(), related_process)
        complete[key] = True
        #print("complete: ", complete)

        # check if there are conditions which make it not complete
        is_complete = True
        for related_sobject in related_sobjects:
            key = "%s|%s|status" % (related_sobject.get_search_key(), related_process)
            if not complete.get(key):
                is_complete = False
                break


        return is_complete




    def get_process_state(self, sobject, process=None):

        if not process:
            process = self.input.get("process")
        if self.input.get("sobject") is not None and sobject.get_search_key() == self.input["sobject"].get_search_key():
            process = self.get_full_process_name(process)
        pipeline_code = process.split('::', 1)[0] if '::' in process else sobject.get_value('pipeline_code', no_exception=True)
        if not pipeline_code and self.input.get('sobject') is not None and sobject.get_search_key() == self.input['sobject'].get_search_key():
            root = (self.input.get('parent_pipelines') or [self.input.get('pipeline')])[0]
            pipeline_code = root.get_code() if root else ''

        key = "Workflow|process_state|%s" % sobject.get_search_key()
        process_states_dict = Container.get(key)
        if process_states_dict is None:
            process_states_dict = {}
            Container.put(key, process_states_dict)

            """
            if sobject.get_base_search_type() == 'sthpw/virtual':
                process_state = SearchType.create("config/process_state")
                process_state.set_sobject_value(sobject)
                process_state.set_value("process", process)

                process_states_dict[process] = process_state
                return process_state
            """

            search = Search("config/process_state?project=" + sobject.get_project_code())
            search.add_sobject_filter(sobject)
            cache_process_states = search.get_sobjects()

            for cache_process_state in cache_process_states:
                cache_process = cache_process_state.get_value("process")
                owner = cache_process_state.get_value('pipeline_code') or sobject.get_value('pipeline_code', no_exception=True)
                process_states_dict[(owner, cache_process)] = cache_process_state


        process_state = process_states_dict.get((pipeline_code, process))
        if not process_state:
            process_state = SearchType.create("config/process_state?project=" + sobject.get_project_code())
            process_state.set_sobject_value(sobject)
            process_state.set_value("process", process)
            process_state.set_value('pipeline_code', pipeline_code)
            _commit_effect(process_state, sobject)

            process_states_dict[(pipeline_code, process)] = process_state

        return process_state


    def get_process_status(self, sobject, process=None):
        if not process:
            process = self.input.get("process")
        if self.input.get("sobject") is not None and sobject.get_search_key() == self.input["sobject"].get_search_key():
            process = self.get_full_process_name(process)

        #TODO: use process_state (instead of messaging)
        status = ""
        key = "%s|%s|status" % (sobject.get_search_key(), process)
        search = Search("sthpw/message")
        search.add_filter('code', key)
        message_sobj = search.get_sobject()
        if message_sobj:
            message = message_sobj.get_json_value("message")
            status = message

        return status



    def log_message(self, sobject, process, status):
        process = self.get_full_process_name(process)
        # need to use API for now
        key = "%s|%s|status" % (sobject.get_search_key(), process)
        from pyasm.command import message as server
        _log_message(sobject, key, status)

        # TODO use process state.
        # status and state will be transitioned to process_state (instead of messaging)
        if sobject.get_base_search_type() != "sthpw/virtual":
            process_state = self.get_process_state(sobject, process)
            process_state.set_value("status", status)
            if not process_state.get_value('pipeline_code'):
                process_state.set_value('pipeline_code', sobject.get_value('pipeline_code', no_exception=True))
            _commit_effect(process_state, sobject)
            if status in ("pending", "in_progress", "revise", "reject", "error"):
                states = Container.get("Workflow|process_state|%s" % sobject.get_search_key()) or {}
                overall = states.get((process_state.get_value('pipeline_code'), self.get_full_process_name("__PIPELINE__")))
                if overall and overall.get_value("status") == "complete":
                    overall.set_value("status", "in_progress")
                    _commit_effect(overall, sobject)




    def get_state(self):

        # NOTE: use messagings for now
        key = "%s|%s|state" % (self.sobject.get_search_key(), self.get_full_process_name(self.process))

        from pyasm.command import message as server

        message = server.get_message(key)
        state = jsonloads(message.get("message")) if message.get("message") else {"packages": {}, "data": {}}

        """
        search = Search(state_type)
        search.add_filter("search_key", self.sobject.get_search_key())
        search.add_filter("process", self.process)
        state_sobj = search.get_sobject()
        state = state_sobj.get_json_value("state")
        """

        return state



class BaseWorkflowNodeHandler(BaseProcessTrigger):

    def __init__(self, **kwargs):
        super(BaseWorkflowNodeHandler, self).__init__(**kwargs)
        self.kwargs = kwargs
        self.input = kwargs.get("input")
        self.name = kwargs.get("name")

        self.pipeline = self.input.get("pipeline")
        self.parent_pipelines = self.input.get("parent_pipelines") or []
        self.process = self.input.get("process")
        self.parent_processes = self.input.get("parent_processes") or []
        self.sobject = self.input.get("sobject")

        self.input_data = self.input.get("data")
        self.data = self.input_data

        # NOTE: this may not be necessary anymore because of the use of the Container flag
        self.internal = self.input.get("internal") or False

        if self.process.find(".") != -1:
            parts = self.process.split(".")
            self.process = parts[-1]
            self.process_parts = parts[:-1]
        else:
            self.process_parts = []

        # by default, output packages are the same as the input packages.  A node mae
        # redefine the self.packages structure as it chooses.
        self.input_packages = self.input.get("packages")
        if not self.input_packages:
            self.input_packages = {}
            self.input_packages['default'] = {}
            self.input['packages'] = self.input_packages
        self.packages = self.input_packages
        self.tasks = None


    def set_name(self, name):
        self.name = name



    def store_state(self):

        # NOTE: use messages for now
        key = "%s|%s|state" % (self.sobject.get_search_key(), self.get_full_process_name(self.process))

        from pyasm.command import message as server

        state = {}

        state['data'] = self.data
        state['packages'] = self.packages

        state = jsondumps(state)
        _log_message(self.sobject, key, state)

        """

        state_obj = SearchType.create(state_type)
        state_obj.set_value("search_key", self.sobject.get_search_key())
        state_obj.set_value("process", self.process)

        state = self.output_data
        state_sobj.set_json_value("state", state)

        state_sobj.commit()
        """




    def retrieve_state(self):

        #print("Retrieving state")

        from pyasm.command import message as server

        # NOTE: use messagings for now
        key = "%s|%s|state" % (self.sobject.get_search_key(), self.get_full_process_name(self.process))

        message = server.get_message(key)
        state = message.get("message")
        if state:
            state = jsonloads(state)
        else:
            state = {
                'packages': {},
                'data': {}
            }

        return state



    def restore_state(self):

        state = self.retrieve_state()
        self.packages = state.get("packages")
        self.data = state.get("data")

        return state








    def check_inputs(self):
        pipeline = self.input.get("pipeline")
        process = self.input.get("process")
        sobject = self.input.get("sobject")

        # first check the inputs.  If there is only one input, then
        # skip this check
        input_processes = pipeline.get_input_processes(process, to_attr="input")
        if len(input_processes) <= 1:
            return True


        # check all of the input processes to see if they are all complete
        complete = True
        for input_process in input_processes:

            input_complete = self.is_complete(input_process)
            if input_complete == False:
                complete = False
                break

            """
            key = "%s|%s|status" % (sobject.get_search_key(), input_process.get_name())
            message_sobj = Search.get_by_code("sthpw/message", key)
            if message_sobj:
                message = message_sobj.get_json_value("message")
                if message not in ["complete", "not_required"]:
                    complete = False
                    break
            else:
                # look for some other means to determine if this is done
                search = Search("sthpw/task")
                search.add_parent_filter(sobject)
                search.add_filter("process", input_process.get_name())
                task = search.get_sobject()
                if task:
                    task_status = task.get("status")
                    task_status = task_status.lower().replace(" ", "_")
                    if task_status not in ["complete", 'not_required']:
                        complete = False
                        break
            """

        if not complete:
            return False
        else:
            return True



    def is_complete(self, input_process):
        pipeline = self.input.get("pipeline")
        sobject = self.input.get("sobject")
        process = self.input.get("process")

        complete = True

        # TODO: look at process state

        key = "%s|%s|status" % (sobject.get_search_key(), self.get_full_process_name(input_process.get_name()))
        search = Search("sthpw/message")
        search.add_filter('code', key)
        message_sobj = search.get_sobject()

        if message_sobj:
            message = message_sobj.get_json_value("message")
            if message not in ["complete", "approved", "not_required"]:
                complete = False
        else:
            # look for some other means to determine if this is done
            search = Search("sthpw/task")
            search.add_parent_filter(sobject)
            search.add_filter("process", self.get_full_process_name(input_process.get_name()))
            task = search.get_sobject()
            if task:
                task_status = task.get("status")
                task_status = task_status.lower().replace(" ", "_")
                if task_status not in ["complete", 'approved', 'not_required']:
                    complete = False
            # if there is no task and this is a manual node, then this is not blocked
            else:
                process_obj = input_process
                node_type = process_obj.get_type()
                if node_type not in ['manual', 'approval']:
                    # NOTE: at some point, we should have an has_task method to deal with
                    # this list
                    complete = False

        return complete



    def handle_pending(self):

        _check_workflow(self.input)
        if not self.check_inputs():
            return

        # simply calls action
        self.log_message(self.sobject, self.process, "pending")
        self.set_all_tasks(self.sobject, self.process, "pending")
        self.run_callback(self.pipeline, self.process, "pending")

        Trigger.call(self, "process|action", output=self.input)


    def handle_action(self):

        _check_workflow(self.input)
        self.log_message(self.sobject, self.process, "in_progress")
        self.set_all_tasks(self.sobject, self.process, "in_progress")
        self.run_callback(self.pipeline, self.process, "action")

        Trigger.call(self, "process|complete", output=self.input)




    def get_output_packages(self):
        '''build the output packages based on the checks of the current process node'''
        _check_workflow(self.input)
        full_process = self.get_full_process_name(self.process)


        # TODO: need to define which package names are created for a node
        #package_names = ["default", "asset"]
        package_names = ["default", "message"]

        # get the packages data structure
        packages = self.packages or {}

        for package_name in package_names:

            # get the existing package
            package = packages.get(package_name)

            # create one if it does not exist
            if not package:
                package = {}
                packages[package_name] = package

            # These are the two original built-in output packages.
            package_type = "snapshot" if package_name == "default" else "message"

            package['type'] = package_type


            # based on the type, create the package
            if package_type == "message":
                # leave alone
                pass
            elif package_type == "snapshot":

                # This package type contains a list search code retrieved by the process
                status = "Final"

                from pyasm.biz import Snapshot
                search = Search("sthpw/snapshot")
                search.add_filter("process", full_process)
                search.add_filter("is_latest", True)
                search.add_filter("status", status)
                search.add_parent_filter(self.sobject)
                snapshots = search.get_sobjects()

                if not snapshots:
                    # then get all of the checked in files?
                    search = Search("sthpw/snapshot")
                    search.add_filter("process", full_process)
                    search.add_filter("is_latest", True)
                    search.add_parent_filter(self.sobject)
                    snapshots = search.get_sobjects()



                snapshot_codes = [x.get_code() for x in snapshots]
                package['snapshot_codes'] = snapshot_codes

        return packages




    def handle_complete(self):

        # run a nodes complete trigger
        _check_workflow(self.input)
        status = self.input.get("status")
        if not status:
            status = "Complete"

        self.log_message(self.sobject, self.process, status)
        self.set_all_tasks(self.sobject, self.process, status)

        self.run_callback(self.pipeline, self.process, status)

        process_obj = self.pipeline.get_process(self.process)



        self.output_data = self.data
        process_sobj = self.get_process_sobj()
        if process_sobj:
            workflow = process_sobj.get_json_value("workflow", {})
        else:
            workflow = {}



        process_output = workflow.get("output") or {}



        # These are currently in Manual node.  Note sure if it should be generic to all nodes
        #packages = self.get_output_packages()
        #self.store_state()

        # call the process|pending event for all output processes
        # (for not required, call process|not_required)
        output_processes = self.pipeline.get_output_processes(self.process)
        for output_process in output_processes:
            output_process = output_process.get_name()

            #if self.process_parts:
            #    output_process = "%s.%s" % (self.process_parts[0], output_process)


            output = {
                'pipeline': self.pipeline,
                'sobject': self.sobject,
                'parent_pipelines': self.parent_pipelines,
                'parent_processes': self.parent_processes,
                'calling_process': self.process,
                'process': output_process,
                'data': self.output_data,
                'packages': self.packages
            }

            if status == "not_required":
                event = "process|not_required"
            else:
                event = "process|pending"

            Trigger.call(self, event, output)


        # if there are no output processes then check for any hierarchy
        if not output_processes and self.parent_processes:
            if any(self.get_process_status(self.sobject, node.get_name()) not in ("complete", "approved", "not_required")
                   for node in self.pipeline.get_processes()
                   if not self.pipeline.get_output_processes(node.get_name())):
                return
            # send a message up the hierarchy
            parent_pipelines = self.parent_pipelines[:]


            pipeline = parent_pipelines.pop()

            parent_processes = self.parent_processes[:]
            process = parent_processes.pop()

            output = {
                'sobject': self.sobject,
                'pipeline': pipeline,
                'parent_pipelines': parent_pipelines,
                'parent_processes': parent_processes,
                'process': process,
                'data': self.output_data,
                'packages': self.packages
            }

            event = "process|complete"
            Trigger.call(self, event, output)


    def handle_not_required(self):
        _check_workflow(self.input)
        if not self.check_not_required_inputs():
            return

        self.input["status"] = "not_required"
        #return self.handle_complete()
        return self._handle_not_required()


    def _handle_not_required(self):

        # run a nodes trigger
        status = self.input.get("status")
        self.log_message(self.sobject, self.process, status)
        self.set_all_tasks(self.sobject, self.process, status)

        self.run_callback(self.pipeline, self.process, status)

        process_obj = self.pipeline.get_process(self.process)



        self.output_data = self.data
        process_sobj = self.get_process_sobj()
        if process_sobj:
            workflow = process_sobj.get_json_value("workflow", {})
        else:
            workflow = {}



        process_output = workflow.get("output") or {}



        # These are currently in Manual node.  Note sure if it should be generic to all nodes
        #packages = self.get_output_packages()
        #self.store_state()



        # call the process|pending event for all output processes
        # (for not required, call process|not_required)
        output_processes = self.pipeline.get_output_processes(self.process)
        for output_process in output_processes:
            output_process = output_process.get_name()

            # if output_process is already in not_required or complete status, skip.
            if self.get_process_status(self.sobject, output_process) in ["not_required", "complete"]:
                return


            #if self.process_parts:
            #    output_process = "%s.%s" % (self.process_parts[0], output_process)

            output = {
                'pipeline': self.pipeline,
                'sobject': self.sobject,
                'parent_pipelines': self.parent_pipelines,
                'parent_processes': self.parent_processes,
                'calling_process': self.process,
                'process': output_process,
                'data': self.output_data,
                'packages': self.packages
            }

            if status == "not_required":
                event = "process|not_required"
            else:
                event = "process|pending"

            Trigger.call(self, event, output)



    def check_not_required_inputs(self):
        pipeline = self.input.get("pipeline")
        process = self.input.get("process")
        sobject = self.input.get("sobject")

        # first check the inputs.  If there is only one input, then
        # skip this check
        input_processes = pipeline.get_input_processes(process, to_attr="input")
        if len(input_processes) <= 1:
            return True


        # check all of the input processes to see if they are all complete
        complete = True
        for input_process in input_processes:

            input_complete = self.is_not_required(input_process)

            if input_complete == False:
                complete = False
                break

        if not complete:
            return False
        else:
            return True


    def is_not_required(self, input_process):
        pipeline = self.input.get("pipeline")
        sobject = self.input.get("sobject")
        process = self.input.get("process")

        complete = True

        # TODO: look at process state


        key = "%s|%s|status" % (sobject.get_search_key(), self.get_full_process_name(input_process.get_name()))
        search = Search("sthpw/message")
        search.add_filter('code', key)
        message_sobj = search.get_sobject()
        if message_sobj:
            message = message_sobj.get_json_value("message")
            if message not in ["not_required"]:
                complete = False
        else:
            # look for some other means to determine if this is done
            search = Search("sthpw/task")
            search.add_parent_filter(sobject)
            search.add_filter("process", self.get_full_process_name(input_process.get_name()))
            task = search.get_sobject()
            if task:
                task_status = task.get("status")
                task_status = task_status.lower().replace(" ", "_")
                if task_status not in ['not_required']:
                    complete = False
            # if there is no task and this is a manual node, then this is not blocked
            else:
                process_obj = input_process
                node_type = process_obj.get_type()
                if node_type not in ['manual', 'approval']:
                    # NOTE: at some point, we should have an has_task method to deal with
                    # this list
                    complete = False


        return complete



    def handle_reject(self):

        _check_workflow(self.input)
        self.log_message(self.sobject, self.process, "reject")
        self.run_callback(self.pipeline, self.process, "reject")

        # set all tasks in the process to revise
        self.set_all_tasks(self.sobject, self.process, "reject")

        process_obj = self.pipeline.get_process(self.process)

        reject_processes = self.input.get("reject_process") or []

        # send revise single to previous processes
        input_processes = self.pipeline.get_input_processes(self.process)
        for input_process in input_processes:
            input_process = input_process.get_name()

            if reject_processes and input_process not in reject_processes:
                continue

            if self.process_parts:
                input_process = "%s.%s" % (self.process_parts[0], input_process)


            error = self.input.get("error")

            input = {
                'pipeline': self.pipeline,
                'sobject': self.sobject,
                'process': input_process,
                'parent_pipelines': self.parent_pipelines,
                'parent_processes': self.parent_processes,
                'error': self.input.get("error") or "Reject from %s" % self.process,
            }

            event = "process|revise"
            Trigger.call(self, event, input)



    def handle_revise(self):

        _check_workflow(self.input)
        self.log_message(self.sobject, self.process, "revise")
        self.run_callback(self.pipeline, self.process, "revise")

        # set all tasks in the process to revise
        tasks = self.set_all_tasks(self.sobject, self.process, "revise")

        # if there is a task on this node, then a revise message does not go back
        # because the task is used to notify
        #if tasks:
        #    return


        process_obj = self.pipeline.get_process(self.process)

        error = self.input.get("error")

        # send revise single to previous processes
        input_processes = self.pipeline.get_input_processes(self.process)
        for input_process in input_processes:
            input_process = input_process.get_name()

            if self.process_parts:
                input_process = "%s.%s" % (self.process_parts[0], input_process)


            input = {
                'pipeline': self.pipeline,
                'sobject': self.sobject,
                'parent_pipelines': self.parent_pipelines,
                'parent_processes': self.parent_processes,
                'process': input_process,
                'error': self.input.get("error")
            }

            event = "process|revise"
            Trigger.call(self, event, input)



class WorkflowDisabledNodeHandler(BaseWorkflowNodeHandler):

    def handle_pending(self):
        _check_workflow(self.input)
        if not self.check_inputs():
            return

        return self.handle_not_required()

    def handle_complete(self):
        _check_workflow(self.input)
        return self.handle_not_required()




class WorkflowManualNodeHandler(BaseWorkflowNodeHandler):

    def handle_pending(self):


        _check_workflow(self.input)
        if not self.check_inputs():
            return

        # simply calls action
        self.log_message(self.sobject, self.process, "pending")


        mapped_status = "Pending"
        to_status = mapped_status

        """

        status_package = self.packages.get("status")
        if status_package:
            to_status = status_package.get("status")

            if to_status:
                mapped_status = to_status

            scope = status_package.get("scope")
            if scope != "stream":
                # remove package
                self.packages.pop("status")
            Trigger.call(self, "process|not_approved", output=self.input)
            return
        """

        process_sobj = self.get_process_sobj()

        # check if tasks need to be autocreated
        autocreate_task = False

        if process_sobj:
            workflow = process_sobj.get_json_value("workflow", {})
            version = workflow.get("version") or 1
            version_2 = version in [2, '2']

            properties = workflow.get("properties") or {}

            autocreate_task = properties.get("autocreate_task") if version_2 else workflow.get("autocreate_task")
            task_creation = properties.get("task_creation") if version_2 else workflow.get("task_creation")

            if autocreate_task in ['true', True]:
                autocreate_task = True
            if task_creation in ['none']:
                autocreate_task = True

            process_obj = self.pipeline.get_process(self.process)
            if not process_obj:
                return

            # only if it's not internal. If it's true, set_all_tasks() returns anyways
            # this saves unnecessary map lookup
            if not self.internal:
                mapped_status = self.get_mapped_status(process_obj, to_status)



        # check to see if the tasks exist and if they don't then create one
        if autocreate_task:

            full_process_name = self.get_full_process_name(self.process)
            tasks = Task.get_by_sobject(self.sobject, process=full_process_name)
            start_date = None
            if not tasks:
                # find
                input_processes = self.pipeline.get_input_process_names(self.process)
                for input_process in input_processes:
                    tasks = Task.get_by_sobject(self.sobject, process=input_process)
                    for task in tasks:
                        end_date = task.get_value("bid_end_date")
                        if not start_date or end_date > start_date:
                            start_date = end_date


                # If we are creating new tasks here, then the status will be set to Assignment
                if not to_status:
                    to_status = "Assignment"
                mapped_status = self.get_mapped_status(process_obj, to_status)
                parent_process = self.get_full_process_name('__PARENT__').rsplit('/', 1)[0] if self.parent_processes else None
                tasks = Task.add_initial_tasks(self.sobject, pipeline_code=self.pipeline.get_code(), processes=[self.process], status=mapped_status, start_date=start_date, parent_process=parent_process)

            else:
                if not to_status:
                    to_status = "Pending"
                mapped_status = self.get_mapped_status(process_obj, to_status)
                tasks = self.set_all_tasks(self.sobject, self.process, mapped_status)
        else:
            tasks = self.set_all_tasks(self.sobject, self.process, mapped_status)


        self.tasks = tasks

        self.run_callback(self.pipeline, self.process, "pending")


        # store the state so that it can be remembered until the next status change
        self.store_state()


        if not self.tasks:
            Trigger.call(self, "process|action", output=self.input)


    def get_mapped_status(self, process_obj, status="Pending"):
        '''Get what status is mapped to Pending'''
        mapped_status = status

        # NOTE: DISABLING this until better search mechanism is used
        """
        status_pipeline_code = process_obj.get_task_pipeline()
        search = Search("config/process")
        search.add_op_filters([("workflow", "like","%Pending%")])
        search.add_filter("pipeline_code", status_pipeline_code)
        pending_process_sobj = search.get_sobject()
        if pending_process_sobj:
            # verify
            workflow = pending_process_sobj.get_json_value("workflow", {})
            mapping = workflow.get('mapping')

            if mapping == 'Pending':
                mapped_status = pending_process_sobj.get_value('process')
        """


        return mapped_status



    def handle_action(self):


        # if tasks was not set yet, then check for the tasks
        _check_workflow(self.input)
        if self.tasks == None:
            full_process_name = self.get_full_process_name(self.process)
            self.tasks = Task.get_by_sobject(self.sobject, process=full_process_name)


        # go to complete if there are no tasks
        if not self.tasks:
            Trigger.call(self, "process|complete", output=self.input)

        else:
            process = self.input.get("process")
            # store the state
            self.store_state()
            self.log_message(self.sobject, self.process, "in_progress")


    def handle_complete(self):

        #status = "complete"
        _check_workflow(self.input)
        status = self.input.get("status") or "complete"

        # restore the state of the node
        state = self.restore_state()


        pipeline = self.input.get("pipeline")
        process = self.input.get("process")
        sobject = self.input.get("sobject")

        # Handle remapped status.
        process_sobj = self.get_process_sobj(pipeline, process)
        if process_sobj:
            workflow = process_sobj.get_json_value("workflow", {})
        else:
            workflow = {}
        version = workflow.get("version") or 1
        version_2 = version in [2, '2']

        properties = workflow.get("properties") or {}

        status_pipeline_code = pipeline.get_process(process).get_task_pipeline()
        #print("status_pipeline_code:", status_pipeline_code)

        status_pipeline = None
        if status_pipeline_code:
            status_pipeline = Pipeline.get_by_code(status_pipeline_code)


        # if this is coming from an internal message (such task status),
        # make sure all of the tasks are complete
        is_complete = True

        if self.input.get("internal") == True:
            full_process_name = self.get_full_process_name(process)
            tasks = Task.get_by_sobject(self.sobject, process=full_process_name)
            # Make sure all of the tasks are complete
            for task in tasks:
                #self.log_message(self.sobject, self.process, status)

                task_status = task.get_value("status")

                # For remapped status
                if status_pipeline:
                    status_node = status_pipeline.get_process(task_status)
                    mapping = status_node.get_attribute('mapping') if status_node else None
                    status_process_sobj = self.get_process_sobj(status_pipeline, task_status)
                    if status_process_sobj:
                        workflow_data = status_process_sobj.get_json_value("workflow", {})
                        mapping = mapping or workflow_data.get("mapping")
                    if mapping:
                        task_status = mapping
                if task_status.lower().replace(" ","_") not in ['complete','approved','not_required']:
                    is_complete = False
                    break


        if not is_complete:
            return

        # build a standard output package
        self.packages = self.get_output_packages()

        # store the state
        self.store_state()
        return super(WorkflowManualNodeHandler, self).handle_complete()




    def handle_not_required(self):
        _check_workflow(self.input)
        status = "not_required"

        # restore the state of the node
        state = self.restore_state()

        pipeline = self.input.get("pipeline")
        process = self.input.get("process")
        sobject = self.input.get("sobject")

        # Handle remapped status.
        process_sobj = self.get_process_sobj(pipeline, process)
        workflow = process_sobj.get_json_value("workflow", {})
        version = workflow.get("version") or 1
        version_2 = version in [2, '2']

        properties = workflow.get("properties") or {}

        # we need to check if the process is already complete. if so, just return.
        if self.get_process_status(self.sobject, process) in ["not_required", "complete"]:
            return


        # build a standard output package
        self.packages = self.get_output_packages()

        # store the state
        self.store_state()

        return super(WorkflowManualNodeHandler, self).handle_not_required()






    def handle_reject(self):
        #self.input['error'] = "Rejected from '%s'" % self.process
        _check_workflow(self.input)
        return super(WorkflowManualNodeHandler, self).handle_reject()



    def handle_revise(self):

        _check_workflow(self.input)
        process = self.input.get("process")
        sobject = self.input.get("sobject")

        error = self.input.get("error")
        if error:
            context = "%s/error" % process
            previous = Container.get('Workflow:note_source')
            Container.put('Workflow:note_source', sobject)
            try:
                Note.create(sobject, error, context=context)
            finally:
                Container.put('Workflow:note_source', previous)

        self.log_message(self.sobject, self.process, "revise")
        self.run_callback(self.pipeline, self.process, "revise")
        # set all tasks in the process to revise
        self.set_all_tasks(self.sobject, self.process, "revise")

        # Manual tasks stop here
        #return super(WorkflowManualNodeHandler, self).handle_revise()






class WorkflowActionNodeHandler(BaseWorkflowNodeHandler):


    def handle_pending(self):
        _check_workflow(self.input)
        if not self.check_inputs():
            return


        # simply calls action
        Trigger.call(self, "process|action", output=self.input)



    def handle_action(self):
        #print("action: ", self.process)

        _check_workflow(self.input)
        self.log_message(self.sobject, self.process, "in_progress")
        self.set_all_tasks(self.sobject, self.process, "in_progress")


        process_obj = self.pipeline.get_process(self.process)
        process_sobj = self.get_process_sobj()

        # get the node's triggers

        triggers = {}
        if process_sobj:
            triggers = process_sobj.get_json_value("workflow")
        if not triggers:
            triggers = {}

        action = triggers.get("on_action")
        cbjs_action = triggers.get("cbjs_action")
        action_path = triggers.get("on_action_path")
        kwargs, input = self.build_trigger_input()
        output = {}

        if action or action_path:
            from tactic.command import PythonCmd
            if action:
                cmd = PythonCmd(code=action, input=input, output=output, **kwargs)
            else:
                cmd = PythonCmd(script_path=action_path, input=input, output=output, **kwargs)

            ret_val = cmd.execute()


        elif cbjs_action:
            raise UnsupportedContract("Server JavaScript callbacks are not migrated")
        else:
            # or call an action trigger
            triggers = Trigger.call(self, "process|action", input, process=process_sobj.get_code())
            # for now set it to true
            ret_val = True
            for trigger in triggers:
                try:
                    info = trigger.get_info()
                except Exception as e:
                    print("WARNING: trigger [%s] does not support get_info" % trigger)
                    continue

                ret_val = info.get("result")
                if ret_val == None:
                    ret_val = True

                # as soon as one trigger specifies a value other than
                # true, that will take precedence
                if ret_val not in [True, 'true']:
                    break



        # store state after the action has been completed
        #self.store_state()


        # copy the output from the scripts into the data structur that will be sent on
        for name, value in output.items():
            self.input[name] = value


        if ret_val in [False, 'false']:
            Trigger.call(self, "process|reject", self.input)
        elif ret_val in [True, 'true', None, ""]:
            Trigger.call(self, "process|complete", self.input)
        elif ret_val in ["block", "wait"]:
            # NOTE: consider adding a "wait" message directly in the workflow
            pass
        else:
            Trigger.call(self, "process|%s" % ret_val, self.input)



class WorkflowApprovalNodeHandler(BaseWorkflowNodeHandler):

    def handle_pending(self):
        _check_workflow(self.input)
        self.log_message(self.sobject, self.process, "pending")

        process_sobj = self.get_process_sobj()

        assigned = None
        if process_sobj:
            workflow = process_sobj.get_json_value("workflow", {})
            version = workflow.get("version") or 1
            version_2 = version in [2, '2']

            if version_2:
                data = workflow.get("data") or {}
                if data:
                    assigned = data.get("assigned")
            else:
                if workflow:
                    assigned = workflow.get("assigned")


        # check to see if the tasks exist and if they don't then create one
        tasks = Task.get_by_sobject(self.sobject, process=self.get_full_process_name(self.process))

        if not tasks:
            parent_process = self.get_full_process_name('__PARENT__').rsplit('/', 1)[0] if self.parent_processes else None
            tasks = Task.add_initial_tasks(self.sobject, pipeline_code=self.pipeline.get_code(), processes=[self.process], assigned=assigned, parent_process=parent_process)
        else:
            self.store_state()
            tasks = self.set_all_tasks(self.sobject, self.process, "pending")

        self.tasks = tasks


        Trigger.call(self, "process|action", self.input)




    def handle_action(self):

        # if tasks was not set yet, then check for the tasks
        _check_workflow(self.input)
        if self.tasks == None:
            full_process_name = self.get_full_process_name(self.process)
            self.tasks = Task.get_by_sobject(self.sobject, process=full_process_name)

        # go to complete if there are no tasks
        if not self.tasks:
            Trigger.call(self, "process|complete", output=self.input)

        else:
            # store the state
            self.store_state()
            self.log_message(self.sobject, self.process, "in_progress")




    def handle_complete(self):
        # restore the state
        _check_workflow(self.input)
        restore_state = True
        if restore_state:
            state = self.retrieve_state()
            self.packages = state.get("packages")
            self.data = state.get("data")

        return super(WorkflowApprovalNodeHandler, self).handle_complete()





    def handle_reject(self):
        _check_workflow(self.input)
        login = Environment.get_login()
        display_name = login.get("display_name")
        if not display_name:
            display_name = login.get_code()
        self.input['error'] = "Approval from '%s' Rejected" % display_name

        return super(WorkflowApprovalNodeHandler, self).handle_reject()




class WorkflowHierarchyNodeHandler(BaseWorkflowNodeHandler):

    def handle_pending(self):
        _check_workflow(self.input)

        # DISABLE for now
        #if not self.check_inputs():
        #    return

        # simply calls action
        if not self.check_inputs():
            return
        Trigger.call(self, "process|action", output=self.input)




    def handle_action(self):
        _check_workflow(self.input)
        self.log_message(self.sobject, self.process, "in_progress")
        self.set_all_tasks(self.sobject, self.process, "in_progress")


        search = Search("config/process")
        search.add_filter("pipeline_code", self.pipeline.get_code())
        search.add_filter("process", self.process)
        process_sobj = search.get_sobject()
        process_code = process_sobj.get_code()


        # use child process
        subpipeline_code = process_sobj.get_value("subpipeline_code")
        if not subpipeline_code:
            workflow = process_sobj.get_json_value("workflow", default={})
            default = workflow.get('default')
            if default:
                subpipeline_code = default.get('subpipeline')

        if subpipeline_code:
            subpipeline = Search.get_by_code("sthpw/pipeline", subpipeline_code)
        else:
            search = Search("sthpw/pipeline")
            search.add_filter("parent_process", process_code)
            subpipeline = search.get_sobject()

        if not subpipeline:
            raise ValueError("Hierarchy process [%s] requires a subpipeline" % self.process)


        # get the input nodes
        child_processes = subpipeline.get_processes(type=['input'])

        if not child_processes:
            child_processes = subpipeline.get_processes()

        if child_processes:
            first_process = child_processes[0]
            first_name = first_process.get_name()

            full_name = "%s/%s" % (self.process, first_name)
            
            parent_pipelines = [self.pipeline]
            parent_processes = [self.process]
            if self.input.get("parent_pipelines"):
                parent_pipelines = self.input.get("parent_pipelines") + parent_pipelines
            if self.input.get("parent_processes"):
                parent_processes = self.input.get("parent_processes") + parent_processes

            input = {
                    'pipeline': subpipeline,
                    'sobject': self.sobject,
                    'process': first_name,
                    'parent_pipelines': parent_pipelines,
                    'parent_processes': parent_processes,
                    'data': self.data,
                    'packages': self.packages,
            }

            event = "process|pending"
            Trigger.call(self, event, input)










class WorkflowDependencyNodeHandler(BaseWorkflowNodeHandler):

    def _get_settings(self):
        # Original XML attributes take precedence over the saved v1/v2 settings.
        node = self.pipeline.get_process(self.process)
        if node.get_attribute("search_type"):
            return {"related_" + name: node.get_attribute(name)
                    for name in ("search_type", "process", "status", "scope", "wait")} | {
                        "expression": node.get_attribute("expression")}
        definition = self.get_process_sobj()
        workflow = definition.get_json_value("workflow") or {}
        settings = (workflow.get("default") or {}) if workflow.get("version") in (2, "2") and 'default' in workflow else workflow
        return {**settings, **{'related_' + name: settings.get('related_' + name, settings.get(name))
                              for name in ('search_type', 'process', 'status', 'scope', 'wait', 'pipeline_code')}}

    def handle_revise(self):
        _check_workflow(self.input)
        status = "revise"
        self.log_message(self.sobject, self.process, status)
        self.set_all_tasks(self.sobject, self.process, status)
        self.run_callback(self.pipeline, self.process, status)
        return self._handle_dependency(status)

    def handle_reject(self):
        _check_workflow(self.input)
        status = "reject"
        self.log_message(self.sobject, self.process, status)
        self.set_all_tasks(self.sobject, self.process, status)
        self.run_callback(self.pipeline, self.process, status)
        return self._handle_dependency(status)

    def handle_action(self):
        _check_workflow(self.input)
        self.log_message(self.sobject, self.process, "in_progress")
        self.set_all_tasks(self.sobject, self.process, "in_progress")
        self.run_callback(self.pipeline, self.process, "action")
        return self._handle_dependency()

    def _handle_dependency(self, status=None):
        _check_workflow(self.input)
        pipeline = self.pipeline
        process = self.process
        sobject = self.sobject
        settings = self._get_settings()
        related_search_type = settings.get("related_search_type")
        related_process = settings.get("related_process")
        related_scope = settings.get("related_scope")
        related_expression = settings.get("expression")
        if not related_expression and not related_search_type:
            raise ValueError("Dependency process requires related_search_type or expression")
        expression = related_expression or (related_search_type if related_search_type.startswith("@")
                                            else "@SOBJECT(%s)" % related_search_type)
        related_sobjects = Search.eval(expression) if related_scope == "global" and not related_expression else Search.eval(expression, sobjects=[sobject])
        if isinstance(related_sobjects, Search):
            related_sobjects = related_sobjects.get_sobjects()
        related_status = status or settings.get("related_status") or "pending"
        related_status = related_status.lower().replace(" ", "_")
        event = "process|action" if related_status == "in_progress" else "process|" + related_status

        calls = Container.get("Workflow::dependency_calls")
        if calls is None:
            calls = []
            Container.put("Workflow::dependency_calls", calls)
        key = (sobject.get_search_key(), pipeline.get_code(), self.get_full_process_name(process))
        if key in calls:
            raise WorkflowException("Cyclic Workflow dependency: %s" % (key,))
        calls.append(key)
        own_state = self.get_process_state(sobject, process)
        own_data = own_state.get_json_value("state") or {}
        own_data["dependency_dispatching"] = True
        own_state.set_json_value("state", own_data)
        _commit_effect(own_state, sobject)
        try:
            # Validate every target before dispatching the first one.
            targets = []
            for related_sobject in related_sobjects:
                if not isinstance(related_sobject, SObject):
                    raise TypeError("Dependency expression must return SObjects")
                related_sobject = Search.get_by_search_key(related_sobject.get_search_key())
                if related_sobject is None:
                    raise LookupError("Dependency object no longer exists")
                related_pipeline = Pipeline.get_by_code(settings.get("related_pipeline_code")) if settings.get("related_pipeline_code") else Pipeline.get_by_sobject(related_sobject)
                if not related_pipeline or not related_pipeline.get_processes():
                    raise ValueError("Dependency object requires a nonempty pipeline")
                target_process = related_process or related_pipeline.get_process_names()[0]
                if not related_pipeline.get_process(target_process):
                    raise ValueError("Dependency process [%s] does not exist" % target_process)
                child_input = {"sobject": related_sobject, "pipeline": related_pipeline, "process": target_process,
                               "status": related_status, "data": self.data, "packages": self.packages,
                               "related_sobject": sobject, "related_pipeline": pipeline,
                               "related_process": process, "dependency_run": True}
                _check_workflow(child_input)
                reader = BaseProcessTrigger()
                reader.input = child_input
                targets.append((related_sobject, child_input, reader))

            for related_sobject, child_input, reader in targets:
                pipeline_state = reader.get_process_state(related_sobject, "__PIPELINE__")
                overall = pipeline_state.get_value("status")
                if child_input['pipeline'].get_code() == related_sobject.get_value('pipeline_code', no_exception=True):
                    overall = related_sobject.get_value("status", no_exception=True) or overall
                if overall.lower() in ("complete", "approved", "not_required") and status not in ("revise", "reject"):
                    continue
                running = pipeline_state.get_value("status") == "in_progress" and reader.get_process_status(related_sobject, child_input["process"]) in ("pending", "in_progress")
                state = pipeline_state.get_json_value("state") or {}
                # Retain the original caller fields; the list prevents lost concurrent waiters.
                caller = {"related_sobject": sobject.get_search_key(), "related_pipeline": pipeline.get_code(),
                          "related_process": process, "related_namespace": "__DEFAULT__",
                          "parent_pipelines": [parent.get_code() for parent in self.parent_pipelines],
                          "parent_processes": self.parent_processes, "data": self.data, "packages": self.packages}
                waiters = state.get("callers") or []
                waiters = [item for item in waiters if (item["related_sobject"], item["related_pipeline"], item["related_process"], item.get("parent_processes") or []) !=
                           (caller["related_sobject"], caller["related_pipeline"], caller["related_process"], caller["parent_processes"])]
                waiters.append(caller)
                state.update(caller)
                state["callers"] = waiters
                pipeline_state.set_value("status", "in_progress")
                pipeline_state.set_json_value("state", state)
                _commit_effect(pipeline_state, related_sobject)
                if not running or status in ("revise", "reject"):
                    Trigger.call(self, event, child_input)
        finally:
            calls.pop()
        own_data["dependency_dispatching"] = False
        own_state.set_json_value("state", own_data)
        _commit_effect(own_state, sobject)
        if status not in ("revise", "reject"):
            Trigger.call(self, "process|complete", self.input)

    def handle_complete(self, status=None):
        _check_workflow(self.input)
        own_state = self.get_process_state(self.sobject, self.process)
        if (own_state.get_json_value("state") or {}).get("dependency_dispatching"):
            return
        if own_state.get_value("status") in ("complete", "approved", "not_required"):
            return
        settings = self._get_settings()
        if settings.get("related_wait") not in (False, "false"):
            related_search_type = settings.get("related_search_type")
            related_expression = settings.get("expression")
            if not related_expression and not related_search_type:
                raise ValueError("Dependency process requires related_search_type or expression")
            expression = related_expression or (related_search_type if related_search_type.startswith("@")
                                                else "@SOBJECT(%s)" % related_search_type)
            related_sobjects = Search.eval(expression) if settings.get("related_scope") == "global" and not related_expression else Search.eval(expression, sobjects=[self.sobject])
            if isinstance(related_sobjects, Search):
                related_sobjects = related_sobjects.get_sobjects()
            for related_sobject in related_sobjects:
                pipeline = Pipeline.get_by_code(settings.get('related_pipeline_code')) if settings.get('related_pipeline_code') else Pipeline.get_by_sobject(related_sobject)
                if pipeline is None:
                    raise LookupError('Dependency pipeline no longer exists')
                reader = BaseProcessTrigger()
                reader.input = {'sobject': related_sobject, 'pipeline': pipeline}
                pipeline_state = reader.get_process_state(related_sobject, "__PIPELINE__")
                value = pipeline_state.get_value("status")
                if pipeline.get_code() == related_sobject.get_value('pipeline_code', no_exception=True):
                    value = related_sobject.get_value("status", no_exception=True) or value
                if value.lower().replace(" ", "_") not in ("complete", "approved", "not_required"):
                    self.log_message(self.sobject, self.process, "in_progress")
                    return
        return super().handle_complete()


#class WorkflowProgressNodeHandler(WorkflowDependencyNodeHandler):
class WorkflowProgressNodeHandler(WorkflowManualNodeHandler):

    def handle_action(self):
        _check_workflow(self.input)
        # does nothing
        self.log_message(self.sobject, self.process, "in_progress")

        # or starts the dependent processes
        #return self._handle_dependency()



    def handle_revise(self):
        _check_workflow(self.input)
        self.log_message(self.sobject, self.process, "revise")
        self.run_callback(self.pipeline, self.process, "revise")
        # set all tasks in the process to revise
        self.set_all_tasks(self.sobject, self.process, "revise")

        process_obj = self.pipeline.get_process(self.process)

        # send revise single to previous processes
        input_processes = self.pipeline.get_input_processes(self.process)
        for input_process in input_processes:
            input_process = input_process.get_name()

            if self.process_parts:
                input_process = "%s.%s" % (self.process_parts[0], input_process)


            input = {
                'pipeline': self.pipeline,
                'sobject': self.sobject,
                'process': input_process,
                'parent_pipelines': self.parent_pipelines,
                'parent_processes': self.parent_processes,
                'data': self.data,
                'packages': self.packages,
            }

            event = "process|revise"
            Trigger.call(self, event, input)







class WorkflowInputNodeHandler(BaseWorkflowNodeHandler):

    def handle_pending(self):
        # fast track to complete
        Trigger.call(self, "process|complete", output=self.input)


class WorkflowOutputNodeHandler(BaseWorkflowNodeHandler):

    def handle_pending(self):
        if not self.check_inputs():
            return
        # fast track to complete
        Trigger.call(self, "process|complete", output=self.input)


    def handle_complete(self):
        if self.parent_processes:
            return super().handle_complete()
        self.log_message(self.sobject, self.process, "complete")

        self.run_callback(self.pipeline, self.process, "complete")


        search = Search("config/process")
        search.add_filter("subpipeline_code", self.pipeline.get_code())
        if self.process_parts:
            search.add_filter("process", self.process_parts[0])
        matches = search.get_sobjects()
        if len(matches) != 1:
            raise ValueError("Output node requires an unambiguous parent pipeline")
        supprocess_sobj = matches[0]
        suppipeline_code = supprocess_sobj.get_value("pipeline_code")
        supprocess = supprocess_sobj.get_value("process")

        suppipeline = Search.get_by_code("sthpw/pipeline", suppipeline_code)
        output = {
            'pipeline': suppipeline,
            'sobject': self.sobject,
            'process': supprocess,
            'data': self.data,
            'packages': self.packages,
        }

        event = "process|complete"
        Trigger.call(self, event, output)




class WorkflowConditionNodeHandler(BaseWorkflowNodeHandler):

    def handle_pending(self):
        _check_workflow(self.input)
        self.log_message(self.sobject, self.process, "pending")
        if not self.check_inputs():
            return

        # fast track to complete - no tasks
        Trigger.call(self, "process|action", output=self.input)


    def handle_action(self):
        _check_workflow(self.input)
        self.log_message(self.sobject, self.process, "in_progress")

        # get the node's triggers
        search = Search("config/process")
        search.add_filter("process", self.process)
        search.add_filter("pipeline_code", self.pipeline.get_code())
        process_sobj = search.get_sobject()
        triggers = {}
        if process_sobj:
            triggers = process_sobj.get_json_value("workflow")
        if not triggers:
            triggers = {}

        self.handle_condition_node(self.sobject, self.pipeline, self.process, triggers)



    def execute_streams(self, streams, event):

        process = self.input.get("process")
        sobject = self.input.get("sobject")
        pipeline = self.input.get("pipeline")

        if not isinstance(streams, list):
            streams = [streams]

        # depending on has_asset_type, we send the appropriate stream

        event = "process|%s" % event

        output_processes = []
        for stream in streams:
            if stream in [True, "Pass"]:
                outputs = pipeline.get_output_processes(process)
            elif stream in [False, "Fail"]:
                outputs = pipeline.get_input_processes(process)
            else:
                outputs = pipeline.get_output_processes(process, from_attr=stream)

            if outputs:
                output_processes.extend(outputs)

        # if there are no output attrs, then check the node names
        if not output_processes:
            outputs = pipeline.get_output_processes(process)
            for output in outputs:
                if output.get_name() in streams:
                    output_processes.append(output)

        called = set()
        for output_process in output_processes:
            output_process_name = output_process.get_name()
            if output_process_name in called:
                continue
            called.add(output_process_name)
            output = {
                'sobject': sobject,
                'pipeline': pipeline,
                'process': output_process_name,
                'data': self.data,
                'packages': self.packages,
                'parent_pipelines': self.parent_pipelines,
                'parent_processes': self.parent_processes,
            }
            Trigger.call(self, event, output)





    def handle_condition_node(self, sobject, pipeline, process, triggers):

        ret_val = self.run_callback(pipeline, process, "action")

        # if a None return value was given, then probably no condition exists
        # yet, so just let if flow through
        if ret_val == None:
            ret_val = True

        # run the completion trigger for this node
        Trigger.call(self, "process|complete", self.input)

        from tactic.command import PythonCmd

        if ret_val == True:
            success_cbk = triggers.get("on_success")
            if success_cbk:
                cmd = PythonCmd(code=success_cbk, sobject=sobject)
                cmd.execute()
                return
            else:
                event = "process|pending"
                attr = "success"
                direction = "output"
                processes = pipeline.get_output_processes(process, from_attr=attr)
                if not processes:
                    attr = None

        elif ret_val == False:

            fail_cbk = triggers.get("on_fail")
            if fail_cbk:
                cmd = PythonCmd(code=fail_cbk, sobject=sobject)
                cmd.execute()
                return
            else:
                event = "process|revise"

                # check to see if there is an output process
                attr = "fail"
                processes = pipeline.get_output_processes(process, from_attr=attr)
                if processes:
                    direction = "output"
                else:
                    direction = "input"
                    attr = None

        else:
            if ret_val == []:
                return

            if isinstance(ret_val, six.string_types):
                ret_val = [ret_val]
            
            all_outputs = pipeline.get_output_processes(process)

            output_processes = []
            output_process_names = []

            not_required_streams = []
            
            
            """
            Two types of return values: stream (from_attr on connector)
            or names of output processes.
                - If streams have been returned, use these streams to 
                  find required processes, and set all other output_processes
                  as not_required.
                - If processes have been returned, set these processes as required,
                  and set all other output_processes as not required.
            """
           
            # Check for streams
            for attr in ret_val:
                outputs = pipeline.get_output_processes(process, from_attr=attr)
                if outputs:
                    for output in outputs:
                        output_processes.append(output)
                        output_process_names.append(output.get_name())
                    

            if output_processes:
                for output in all_outputs:
                    if output.get_name() not in output_process_names:
                        not_required_streams.append(output.get_name())

            
            else:
                for output in all_outputs:
                    if output.get_name() in ret_val:
                        output_processes.append(output)
                        output_process_names.append(output.get_name())
                    else:
                        not_required_streams.append(output.get_name())
            
            self.execute_streams(not_required_streams, "not_required")

            called = set()
            for output_process in output_processes:
                output_process_name = output_process.get_name()

                # skipped alreayd processed
                if output_process_name in called:
                    continue

                event = "process|pending"


                output = {
                    'sobject': sobject,
                    'pipeline': pipeline,
                    'process': output_process_name,
                    'data': self.data,
                    'packages': self.packages,
                    'parent_pipelines': self.parent_pipelines,
                    'parent_processes': self.parent_processes,
                }
                Trigger.call(self, event, output)
                called.add(output_process_name)


            return




        # by default, go back to incoming or outcoming
        if direction == "input":
            processes = pipeline.get_input_processes(process, to_attr=attr)
        else:
            processes = pipeline.get_output_processes(process, from_attr=attr)


        for process in processes:
            process_name = process.get_name()
            output = {
                'sobject': sobject,
                'pipeline': pipeline,
                'process': process_name,
                'data': self.data,
                'packages': self.packages,
                'parent_pipelines': self.parent_pipelines,
                'parent_processes': self.parent_processes,
            }
            Trigger.call(self, event, output)



    def handle_complete(self):
        # run a nodes complete trigger
        _check_workflow(self.input)
        self.log_message(self.sobject, self.process, "complete")
        self.run_callback(self.pipeline, self.process, "complete")

        self.set_all_tasks(self.sobject, self.process, "complete")

        #self.store_state()


###---------------------------------



class ProcessPendingTrigger(BaseProcessTrigger):


    def execute(self):
        # set all task to pending

        _check_workflow(self.input)
        pipeline = self.input.get("pipeline")
        process = self.input.get("process")
        sobject = self.input.get("sobject")

        if process.find(".") != -1:
            parts = process.split(".")
            process = parts[-1]

        if process.find("/") != -1:
            parts = process.split("/")
            process = parts[-1]

        process_obj = pipeline.get_process(process)
        if not process_obj:
            msg = "ERROR: pipeline [%s] does not have a process [%s]" % (pipeline.get_code(), process)
            raise Exception(msg)


        node_type = process_obj.get_type()

        state = "active"

        if state == "disabled":
            handler = WorkflowDisabledNodeHandler(input=self.input)
        elif node_type == "action":
            handler = WorkflowActionNodeHandler(input=self.input)
        elif node_type == "approval":
            handler = WorkflowApprovalNodeHandler(input=self.input)
        elif node_type in ["manual", "node"]:
            handler = WorkflowManualNodeHandler(input=self.input)
        elif node_type == "hierarchy":
            handler = WorkflowHierarchyNodeHandler(input=self.input)
        elif node_type == "input":
            handler = WorkflowInputNodeHandler(input=self.input)
        elif node_type == "output":
            handler = WorkflowOutputNodeHandler(input=self.input)
        elif node_type == "condition":
            handler = WorkflowConditionNodeHandler(input=self.input)
        elif node_type == "dependency":
            handler = WorkflowDependencyNodeHandler(input=self.input)
        elif node_type == "progress":
            handler = WorkflowProgressNodeHandler(input=self.input)
        else:
            handler = self.get_handler(node_type)

        return handler.handle_pending()





class ProcessActionTrigger(BaseProcessTrigger):

    def execute(self):

        # get the pipeline
        _check_workflow(self.input)
        pipeline = self.input.get("pipeline")
        process = self.input.get("process")
        sobject = self.input.get("sobject")

        if process.find(".") != -1:
            parts = process.split(".")
            process = parts[-1]
        if process.find("/") != -1:
            parts = process.split("/")
            process = parts[-1]



        process_obj = pipeline.get_process(process)
        node_type = process_obj.get_type()

        if node_type == "action":
            handler = WorkflowActionNodeHandler(input=self.input)
            return handler.handle_action()
        elif node_type == "approval":
            handler = WorkflowApprovalNodeHandler(input=self.input)
            return handler.handle_action()
        elif node_type in ["manual", "node"]:
            handler = WorkflowManualNodeHandler(input=self.input)
            return handler.handle_action()
        elif node_type == "hierarchy":
            handler = WorkflowHierarchyNodeHandler(input=self.input)
            return handler.handle_action()
        elif node_type == "input":
            handler = WorkflowInputNodeHandler(input=self.input)
            return handler.handle_action()
        elif node_type == "output":
            handler = WorkflowOutputNodeHandler(input=self.input)
            return handler.handle_action()
        elif node_type == "condition":
            handler = WorkflowConditionNodeHandler(input=self.input)
            return handler.handle_action()
        elif node_type == "dependency":
            handler = WorkflowDependencyNodeHandler(input=self.input)
            return handler.handle_action()
        elif node_type == "progress":
            handler = WorkflowProgressNodeHandler(input=self.input)
            return handler.handle_action()
        else:
            handler = self.get_handler(node_type)
            return handler.handle_action()





class ProcessCompleteTrigger(BaseProcessTrigger):

    def get_status(self):
        return "complete"

    def execute(self):

        _check_workflow(self.input)
        process = self.input.get("process")
        sobject = self.input.get("sobject")
        pipeline = self.input.get("pipeline")


        if not pipeline:
            return


        # This checks all the dependent completes to see if they are complete
        # before declaring that this node is complete
        if not self.check_complete_inputs():
            self.log_message(sobject, process, "in_progress")
            return

        if process.find(".") != -1:
            parts = process.split(".")
            process = parts[-1]
        if process.find("/") != -1:
            parts = process.split("/")
            process = parts[-1]


        process_obj = pipeline.get_process(process)
        if process_obj:
            node_type = process_obj.get_type()
        else:
            return


        # switch the status to whatever any derived class states (ie: not_required)
        status = self.get_status()
        self.input['status'] = status


        handler = None
        if node_type == "action":
            handler = WorkflowActionNodeHandler(input=self.input)
        elif node_type == "approval":
            handler = WorkflowApprovalNodeHandler(input=self.input)
        elif node_type in ["manual", "node", "progress"]:
            handler = WorkflowManualNodeHandler(input=self.input)
        elif node_type == "hierarchy":
            handler = WorkflowHierarchyNodeHandler(input=self.input)
        elif node_type == "input":
            handler = WorkflowInputNodeHandler(input=self.input)
        elif node_type == "output":
            handler = WorkflowOutputNodeHandler(input=self.input)
        elif node_type == "condition":
            handler = WorkflowConditionNodeHandler(input=self.input)
        elif node_type == "dependency":
            handler = WorkflowDependencyNodeHandler(input=self.input)
        elif node_type == "progress":
            handler = WorkflowProgressNodeHandler(input=self.input)
        else:
            handler = self.get_handler(node_type)


        if handler:
            if status == "not_required":
                result = handler.handle_not_required()
            else:
                result = handler.handle_complete()
            if self.get_process_status(sobject, process) in ("complete", "approved", "not_required"):
                Trigger.call(sobject, "workflow|listen", self.input)
                Trigger.call(sobject, 'workflow|' + sobject.get_base_search_type(), self.input,
                             process=self.get_full_process_name(process))
            return result


        # Make sure the below is completely deprecated
        assert(False)




class ProcessApproveTrigger(ProcessCompleteTrigger):
    def get_status(self):
        return "approved"


class ProcessNotRequiredTrigger(ProcessCompleteTrigger):
    def get_status(self):
        return "not_required"




class ProcessRejectTrigger(BaseProcessTrigger):

    def get_status(self):
        return "reject"

    def execute(self):

        _check_workflow(self.input)
        process = self.input.get("process")
        sobject = self.input.get("sobject")
        pipeline = self.input.get("pipeline")


        # This checks all the dependent completes to see if they are complete
        # before declaring that this node is complete
        if not self.check_complete_inputs():
            self.log_message(sobject, process, "in_progress")
            return


        #reject_processes = self.input.get("reject_process")

        process_obj = pipeline.get_process(process)
        node_type = process_obj.get_type()


        if node_type == "dependency":
            handler = WorkflowDependencyNodeHandler(input=self.input)
            return handler.handle_reject()
        elif node_type == "progress":
            handler = WorkflowProgressNodeHandler(input=self.input)
            return handler.handle_reject()


        else:
            handler = self.get_handler(node_type)
            return handler.handle_reject()





class ProcessReviseTrigger(ProcessRejectTrigger):

    def get_status(self):
        return "revise"

    def execute(self):
        _check_workflow(self.input)
        pipeline = self.input.get("pipeline")
        process = self.input.get("process")
        sobject = self.input.get("sobject")

        if process.find(".") != -1:
            parts = process.split(".")
            process = parts[-1]

        process_obj = pipeline.get_process(process)
        node_type = process_obj.get_type()

        if node_type == "dependency":
            handler = WorkflowDependencyNodeHandler(input=self.input)
            return handler.handle_revise()
        elif node_type == "progress":
            handler = WorkflowProgressNodeHandler(input=self.input)
            return handler.handle_revise()

        else:
            handler = self.get_handler(node_type)
            return handler.handle_revise()



        process = self.input.get("process")
        sobject = self.input.get("sobject")
        pipeline = self.input.get("pipeline")

        self.log_message(sobject, process, self.get_status())

        process_obj = pipeline.get_process(process)
        node_type = process_obj.get_type()

        self.run_callback(pipeline, process, "revise")

        if node_type in ["condition", "action", "approval"]:

            self.set_all_tasks(sobject, process, "")

            input_processes = pipeline.get_input_processes(process)
            for input_process in input_processes:
                input_process = input_process.get_name()

                input = {
                    'pipeline': pipeline,
                    'sobject': sobject,
                    'process': input_process
                }

                event = "process|revise"
                Trigger.call(self, event, input)


        else:
            self.set_all_tasks(sobject, process, self.get_status())




class ProcessErrorTrigger(BaseProcessTrigger):

    def execute(self):
        process = self.input.get("process")
        sobject = self.input.get("sobject")
        pipeline = self.input.get("pipeline")

        print("Error: Failed to process [%s] on sobject [%s]" % (process, sobject.get_search_key() ))

        # TODO: send a message so that those following this sobject will be notified





class CustomProcessConfig(object):
    """
    <config>
    <youtube>
        <element name="node">
          <display class="YouTubeNodeWdg"/>
        </element>
        <element name="info">
          <display class="YouTubeProcessInfoWdg"/>
        </element>
        <element name="process">
          <display class="YouTubeNodeHandler"/>
        </element>
    </youtube>
    </config>
    """

    def get_config(cls, node_type):

        category = "workflow"

        # cache already search configs
        configs = Container.get("CustomProcessConfig:configs")
        if configs == None:
            configs = {}
            Container.put("CustomProcessConfig:configs", configs)


        config = configs.get(node_type)
        if config == None:
            from pyasm.search import WidgetDbConfig

            search = Search("config/widget_config")
            search.add_filter("category", category)
            search.add_filter("view", node_type)

            config = search.get_sobject()

            configs[node_type] = config



        return config

    get_config = classmethod(get_config)




    def get_node_handler(cls, node_type, extra_options={}):
        raise UnsupportedContract("CustomProcessConfig.get_node_handler requires the remaining Workflow handlers")
        config = cls.get_config(node_type)
        extra_options['node_type'] = node_type
        handler = config.get_display_widget("node", extra_options)
        return handler
    get_node_handler = classmethod(get_node_handler)


    def get_info_handler(cls, node_type, extra_options={}):
        raise UnsupportedContract("CustomProcessConfig.get_info_handler requires the remaining Workflow handlers")
        config = cls.get_config(node_type)
        extra_options['node_type'] = node_type
        handler = config.get_display_widget("info", extra_options)
        return handler
    get_info_handler = classmethod(get_info_handler)


    def get_process_handler(cls, node_type, extra_options={}):
        config = cls.get_config(node_type)
        if config is None:
            raise LookupError('No workflow configuration for [%s]' % node_type)
        extra_options = dict(extra_options, node_type=node_type)
        handler = config.get_display_widget("process", extra_options)
        return handler
    get_process_handler = classmethod(get_process_handler)


    def get_delete_handler(cls, node_type, extra_options={}):
        config = cls.get_config(node_type)
        if config is None or not config.get_display_handler('delete'):
            return ''
        extra_options = dict(extra_options, node_type=node_type)
        handler = config.get_display_widget("delete", extra_options)
        return handler
    get_delete_handler = classmethod(get_delete_handler)


    def get_save_handler(cls, node_type, extra_options={}):
        config = cls.get_config(node_type)
        if config is None or not config.get_display_handler('save'):
            return ''
        extra_options = dict(extra_options, node_type=node_type)

        # save handlers are optional
        handler = config.get_display_widget("save", extra_options)
        return handler
    get_save_handler = classmethod(get_save_handler)







class ProcessCustomTrigger(BaseProcessTrigger):

    def execute(self):
        _check_workflow(self.input)
        process = self.input.get("process")
        sobject = self.input.get("sobject")
        pipeline = self.input.get("pipeline")
        status = self.input.get("status")
        if not isinstance(status, str) or not status:
            raise ValueError("Custom task status is required")
        normalized = status.lower().replace(" ", "_")
        if normalized in PREDEFINED:
            status = normalized

        # A custom status may direct another custom status back to this node.
        path = Container.get("Workflow::custom_status_path")
        if path is None:
            path = set()
            Container.put("Workflow::custom_status_path", path)
        key = (sobject.get_search_key(), self.get_full_process_name(process), status)
        if key in path:
            raise ValueError("Circular custom status transition: %s/%s" % (process, status))
        path.add(key)
        try:
            self.log_message(sobject, process, status)
            self.run_callback(pipeline, process, "custom")

            process_obj = pipeline.get_process(process)
            if not process_obj:
                raise LookupError("Workflow process does not exist: %s" % process)
            status_pipeline_code = process_obj.get_task_pipeline()
            status_pipeline = Pipeline.get_by_code(status_pipeline_code)
            if not status_pipeline:
                raise LookupError("Task status pipeline does not exist: %s" % status_pipeline_code)
            status_obj = status_pipeline.get_process(status)
            if not status_obj:
                # Original unknown statuses remain callback-only.
                return

            process_sobj = self.get_process_sobj(status_pipeline, status)
            workflow = process_sobj.get_json_value("workflow", {}) if process_sobj else {}
            direction = status_obj.get_attribute("direction")
            to_status = status_obj.get_attribute("status")
            mapping = status_obj.get_attribute("mapping") or workflow.get("mapping")
            if not to_status and not mapping:
                direction = workflow.get("direction")
                to_status = workflow.get("status")

            if mapping:
                mapping = mapping.lower().replace(" ", "_")
                if mapping not in PREDEFINED:
                    raise ValueError("Unknown task status mapping: %s" % mapping)
                event = "process|action" if mapping == "in_progress" else "process|%s" % mapping
                Trigger.call(self.get_caller(), event, output=self.input)
            elif to_status:
                normalized = to_status.lower().replace(" ", "_")
                if normalized in PREDEFINED:
                    to_status = normalized
                if direction == "current":
                    processes = [process_obj]
                elif direction == "input":
                    processes = pipeline.get_input_processes(process)
                else:
                    processes = pipeline.get_output_processes(process)
                event = "process|action" if to_status == "in_progress" else "process|%s" % to_status if to_status in PREDEFINED else "process|custom"
                for target in processes:
                    output = dict(self.input, process=target.get_name(), status=to_status, internal=False)
                    output.pop('task', None)
                    Trigger.call(self, event, output)
            else:
                for connect in pipeline.get_output_connects(process):
                    to_process = connect.get_to()
                    if status == connect.get_from_attr() or status == to_process:
                        output = dict(self.input, process=to_process, status=to_status, internal=False)
                        output.pop('task', None)
                        Trigger.call(self, "process|pending", output)
        finally:
            path.remove(key)


class ProcessListenTrigger(BaseProcessTrigger):
    '''class for listeners in the pipeline'''

    def execute(self):

        current_process_name = self.input.get("process")
        current_pipeline = self.input.get("pipeline")
        current_process = ""
        # if it has no pipeline_code set, it should exit
        if current_pipeline:
            current_process = current_pipeline.get_process(current_process_name)
        else:
            return
        current_status = self.input.get("status")
        current_sobject = self.input.get("sobject")


        _check_workflow(self.input)
        # search the process state for data on callers
        pipeline_state = self.get_process_state(current_sobject, "__PIPELINE__")
        state = pipeline_state.get_json_value("state") or {}
        output_processes = current_pipeline.get_output_processes(current_process_name)
        was_complete = pipeline_state.get_value("status") == "complete"
        if not output_processes and all(
                node.get_name() == current_process_name or
                self.get_process_status(current_sobject, node.get_name()) in ("complete", "approved", "not_required")
                for node in current_pipeline.get_processes()
                if not current_pipeline.get_output_processes(node.get_name())):
            # Complete only after the handler and every terminal node have completed.
            pipeline_state.set_value("status", "complete")
            _commit_effect(pipeline_state, current_sobject)
        else:
            return
        if was_complete:
            return


        use_process_state = True
        if use_process_state:

            # set the pipeline to "complete"

            callers = state.get("callers")
            if callers is None:
                callers = [state] if state.get("related_sobject") else []
            if not callers:
                return
            state["callers"] = []
            pipeline_state.set_json_value("state", state)
            _commit_effect(pipeline_state, current_sobject)
            for caller in callers:
                related_sobject = Search.get_by_search_key(caller["related_sobject"])
                if related_sobject is None:
                    continue  # A deleted caller no longer needs a completion event.
                related_pipeline = Pipeline.get_by_code(caller["related_pipeline"])
                parents = [Pipeline.get_by_code(code) for code in caller.get("parent_pipelines") or []]
                if related_pipeline is None or any(parent is None for parent in parents):
                    raise LookupError("Dependency caller pipeline no longer exists")
                input = {'sobject': related_sobject, 'pipeline': related_pipeline,
                         'process': caller["related_process"], 'parent_pipelines': parents,
                         'parent_processes': caller.get("parent_processes") or [],
                         'data': caller.get("data"), 'packages': caller.get("packages")}
                Trigger.call(self, "process|complete", output=input)
            return



        listeners = Container.get("process_listeners")
        if listeners == None:
            # build up a data structure of listeners from the pipelines
            listeners = {}
            Container.put("process_listeners", listeners)


            # FIXME: what if there many many many workflows??
            # should probably go directly to the process table
            """
            search = Search("config/process")
            search.add_filter("workflow->node_type", ["dependency", "progress"], op="in")

            process_sobjs = search.get_sobjects()
            for process_sobj in process_sobjs:
                workflow = process_sobj.get_json_value("workflow") or {}
                settings = workflow.get("default") or {}

                process_name = process_sobj.get_value("process")

                listen_stype = settings.get("search_type")
                listen_status = settings.get("status")
                listen_process_name = settings.get("process")
                listen_pipeline_code = settings.get("pipeline_code")


                if listen_pipeline_code:
                    listen_pipeline = Pipeline.get_by_code(listen_pipeline_code)
                    listen_process = listen_pipeline.get_process(listen_process_name)
                else:
                    listen_pipeline = None
                    listen_process = None


                if listen_pipeline_code:
                    listen_key = "%s:%s:%s:%s" % (listen_stype, listen_pipeline_code, listen_process_name, listen_status)
                else:
                    listen_key = "%s:%s:%s" % (listen_stype, listen_process_name, listen_status)

                items = listeners.get(listen_key)
                if items == None:
                    items = []
                    listeners[listen_key] = items

                items.append( {
                    "pipeline": listen_pipeline,
                    "process": listen_process,
                } )

            """


            search_type = current_sobject.get_base_search_type()
            from pyasm.biz import Schema
            schema = Schema.get()
            related_search_types = schema.get_related_search_types(search_type)
            related_search_types.append(search_type)


            # get all of the pipelines
            search = Search("sthpw/pipeline")
            search.add_filters("search_type", related_search_types)
            listen_pipelines = search.get_sobjects()


            for listen_pipeline in listen_pipelines:
                pipeline_code = listen_pipeline.get_code()
                listen_processes = listen_pipeline.get_processes()

                for listen_process in listen_processes:

                    # FIXME: this is not saved in the workflow anymore
                    listen_stype = listen_process.get_attribute("search_type")

                    listen_status = listen_process.get_attribute("status")
                    listen_pipeline_code = listen_process.get_attribute("pipeline_code")
                    listen_process_name = listen_process.get_attribute("process")

                    if not listen_stype:
                        # get the process sobject
                        search = Search("config/process")
                        search.add_filter("process", listen_process.get_name())
                        search.add_filter("pipeline_code", pipeline_code)
                        process_sobj = search.get_sobject()
                        if not process_sobj:
                            continue

                        workflow = process_sobj.get_json_value("workflow", {})
                        if not workflow:
                            continue

                        listen_stype = workflow.get("search_type")
                        listen_process_name = workflow.get("process")
                        listen_pipeline_code = workflow.get("pipeline_code")
                        listen_status = workflow.get("status")

                    if not listen_stype:
                        continue

                    if not listen_status:
                        listen_status = current_status


                    if listen_pipeline_code:
                        listen_key = "%s:%s:%s:%s" % (listen_stype, listen_pipeline_code, listen_process_name, listen_status)
                    else:
                        listen_key = "%s:%s:%s" % (listen_stype, listen_process_name, listen_status)

                    items = listeners.get(listen_key)
                    if items == None:
                        items = []
                        listeners[listen_key] = items

                    items.append( {
                        "pipeline": listen_pipeline,
                        "process": listen_process,
                    } )



        # need to find any listeners for this status on this process
        search_type = current_sobject.get_base_search_type()
        pipeline_code = current_pipeline.get_value("code")

        key = "%s:%s:%s" % (search_type, current_process, current_status)
        items = listeners.get(key) or []

        key2 = "%s:%s:%s:%s" % (search_type, pipeline_code, current_process, current_status)
        items2 = listeners.get(key2)

        if items2:
            items.extend(items2)


        if not items:
            return

        for item in items:

            listen_pipeline = item.get("pipeline")
            listen_process = item.get("process")

            # these process keys are actually process objects
            input = {
                'pipeline': current_pipeline,
                'sobject': current_sobject,
                'process': current_process,
                'related_pipeline': listen_pipeline,
                'related_process': listen_process,
            }


            # send a complete message to the related pipelines
            self._handle_dependency(input, "complete")


    def _handle_dependency(self, input, status="complete"):

        raise UnsupportedContract("ProcessListenTrigger._handle_dependency requires the remaining Workflow handlers")
        pipeline = input.get("pipeline")
        process_obj = input.get("process")
        process_name = process_obj.get_name()
        sobject = input.get("sobject")

        # attributes for this process
        related_pipeline = input.get("related_pipeline")
        related_process = input.get("related_process")
        related_process_name = related_process.get_name()


        # TODO: this may need to be retrieved from workflow column
        related_scope = related_process.get_attribute("scope")
        related_wait = related_process.get_attribute("wait")


        # get the search type from the related pipeline
        related_search_type = related_pipeline.get_value("search_type")

        if not related_search_type:
            print("WARNING: no related search_type found")
            return

        if not related_process:
            print("WARNING: no related process found")
            return


        # this is currently hard coded since ProcessListenTrigger is only run
        # when ProcessCompleteTrigger is run
        # override related_status with status passed in
        related_status = "complete"


        if related_search_type.startswith("@"):
            expression = related_search_type
        else:
            expression = "@SOBJECT(%s)" % related_search_type


        if related_scope == "global":
            related_sobjects = Search.eval(expression)
        else:
            related_sobjects = Search.eval(expression, sobjects=[sobject])

        for related_sobject in related_sobjects:
            """
            # TOBE commented out
            # if the related_sobject is already complete, don't do anything
            key = "%s|%s|status" % (related_sobject.get_search_key(), related_process)

            message_sobj = Search.get_by_code("sthpw/message", key)
            if message_sobj:
                value = message_sobj.get_value("message")
                if related_status.lower() in ["revise", "reject"]:
                    pass
                elif value == "complete" and value not in ['revise', 'reject']:
                    continue
            """

            # This is for unittests which don't necessarily commit changes
            related_sobject = Search.get_by_search_key(related_sobject.get_search_key())

            related_pipeline = Pipeline.get_by_sobject(related_sobject)
            if not related_process:
                # get the first one
                related_processes = related_pipeline.get_processes()
                related_process = related_processes[0]

            # these conditions are not fully utilized since it's always complete
            if related_status in ["in_progress", "In Progress"]:
                event = "process|action"
            else:
                if related_status.lower() in PREDEFINED:
                    event = "process|%s" % related_status.lower()
                else:
                    event = "process|%s" % related_status


            # inputs are reversed as it sends the message
            input = {
                'sobject': related_sobject,
                'pipeline': related_pipeline,
                'process': related_process_name,
                'related_sobject': sobject,
                'related_pipeline': pipeline,
                'related_process': process_name,
            }


            Trigger.call(self, event, input)

