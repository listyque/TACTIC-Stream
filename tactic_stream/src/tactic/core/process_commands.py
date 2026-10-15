###########################################################
#
# Copyright (c) 2005-2008, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#


"""Original process-property commands over the shared headless kernel.
Trusted callback classes require the active persisted administrator Command.
"""
import os
from pyasm.command import Command
from pyasm.common.errors import UnsupportedContract
from tactic.command.python_cmd import check_script_execution
from pyasm.common import Common, Environment, jsonloads
from pyasm.search import Search, SearchType, SearchKey, SObject
from pyasm.biz import Pipeline, Project, Task
from pyasm.security import Sudo
from tactic_client_lib import TacticServerStub

class ProcessInfoCmd(Command):

    def execute(self):
        check_script_execution()
        node_type = self.kwargs.get("node_type")

        if node_type in ["manual", "node"]:
            return self.handle_manual()

        if node_type in ["action", "condition"]:
            return self.handle_action()

        if node_type == 'dependency':
            return self.handle_dependency()

        if node_type == 'status':
            return self.handle_status()

        if node_type == 'approval':
            return self.handle_approval()

        if node_type == 'hierarchy':
            return self.handle_hierarchy()

        if node_type == 'progress':
            return self.handle_progress()

        # Get custom save cmd via node_type
        from pyasm.command import CustomProcessConfig
        cmd = CustomProcessConfig.get_save_handler(node_type, self.kwargs)
        return cmd.execute() if cmd else self.handle_default()

    def set_description(self, process_sobj):
        description = self.kwargs.get("description")
        if description or description == "":
            process_sobj.set_value("description", description)


    def handle_default(self):


        pipeline_code = self.kwargs.get("pipeline_code")
        process = self.kwargs.get("process")

        search = Search("config/process")
        search.add_filter("pipeline_code", pipeline_code)
        search.add_filter("process", process)
        process_sobj = search.get_sobject()

        description = self.kwargs.get("description")
        if not description:
            return

        process_sobj.set_value("description", description)

        process_sobj.commit()




    def handle_manual(self):

        pipeline_code = self.kwargs.get("pipeline_code")
        process = self.kwargs.get("process")

        search = Search("config/process")
        search.add_filter("pipeline_code", pipeline_code)
        search.add_filter("process", process)
        process_sobj = search.get_sobject()

        self.set_description(process_sobj)
        process_sobj.commit()

        cbk_classes = self.kwargs.get("_cbk_classes") or []

        handled = set()
        for cbk_class in cbk_classes:
            if cbk_class in handled:
                continue
            cmd = Common.create_from_class_path(cbk_class, {}, self.kwargs)
            cmd.execute()
            handled.add(cbk_class)

        settings = process_sobj.get_json_value("workflow") or {}
        node_type = settings.get("node_type") or "manual"
        if node_type in ['manual', 'approval', 'action', 'condition', 'hierarchy', 'progress', 'dependency', 'input', 'output']:
            return

        # Get custom save cmd via node_type
        from pyasm.command import CustomProcessConfig
        cmd = CustomProcessConfig.get_save_handler(node_type, self.kwargs)
        if cmd:
            return cmd.execute()



    def handle_action(self):

        is_admin = Environment.get_security().is_admin()

        action = self.kwargs.get("action") or "create_new"
        script = self.kwargs.get("script")
        script_path = self.kwargs.get("script_path")
        on_action_class = self.kwargs.get("on_action_class")


        # version 1 command handling
        version_str = self.kwargs.get('version') or 1
        version = int(version_str)
        command = self.kwargs.get("command")
        if version == 1 and command:
            action = command.get("action") or "create_new"
            script = command.get("script")
            script_path = command.get("script_path")
            on_action_class = command.get("on_action_class")


        execute_mode = self.kwargs.get("execute_mode")

        pipeline_code = self.kwargs.get("pipeline_code")
        process = self.kwargs.get("process")


        if is_admin:
            language = self.kwargs.get("language")
            if not language:
                language = "python"
        else:
            language = "server_js"

        pipeline = Pipeline.get_by_code(pipeline_code)


        search = Search("config/process")
        search.add_filter("pipeline_code", pipeline_code)
        search.add_filter("process", process)
        process_sobj = search.get_sobject()


        event = "process|action"

        from tactic.core.process_constants import TRIGGER_FOLDER_PREFIX

        folder = "%s/%s" % (TRIGGER_FOLDER_PREFIX, pipeline.get_code())
        title = process_sobj.get_code()

        # check to see if the trigger already exists
        search = Search("config/trigger")
        search.add_filter("event", event)
        search.add_filter("process", process_sobj.get_code())
        trigger = search.get_sobject()
        if not trigger:
            # create a new one
            trigger = SearchType.create("config/trigger")
            trigger.set_value("event", event)
            trigger.set_value("process", process_sobj.get_code())


        if action == "command":
            trigger.set_value("script_path", "NULL", quoted=False)
            trigger.set_value("class_name", on_action_class)

        else:
            if script_path:
                folder, title = os.path.split(script_path)
            else:
                script_path = "%s/%s" % (folder, title)

            if script or self.kwargs.get("script_path"):
                trigger.set_value("script_path", script_path)
            else:
                trigger.set_value("script_path", "NULL", quoted=False)

            trigger.set_value("class_name", "NULL", quoted=False)




        if execute_mode:
            trigger.set_value("mode", execute_mode)


        trigger.commit()

        if script:

            from pyasm.security import Sudo
            sudo = Sudo()
            try:

                # check to see if the script already exists
                search = Search("config/custom_script")
                search.add_filter("folder", folder)
                search.add_filter("title", "%s" % title)
                script_obj = search.get_sobject()
                if not script_obj:
                    script_obj = SearchType.create("config/custom_script")
                    script_obj.set_value("folder", folder)
                    script_obj.set_value("title", "%s" % title)

                script_obj.set_value("language", language)
                script_obj.set_value("script", script)
                script_obj.commit()

            finally:
                sudo.exit()

        self.set_description(process_sobj)
        process_sobj.commit()



    def handle_dependency(self):

        pipeline_code = self.kwargs.get("pipeline_code")
        process = self.kwargs.get("process")

        pipeline = Pipeline.get_by_code(pipeline_code)

        search = Search("config/process")
        search.add_filter("pipeline_code", pipeline_code)
        search.add_filter("process", process)
        process_sobj = search.get_sobject()


        related_search_type = self.kwargs.get("related_search_type")
        related_process = self.kwargs.get("related_process")
        related_status = self.kwargs.get("related_status")
        related_scope = self.kwargs.get("related_scope")
        related_wait = self.kwargs.get("related_wait")

        workflow = process_sobj.get_json_value("workflow")
        if not workflow:
            workflow = {}

        if related_search_type:
            workflow['search_type'] = related_search_type
        if related_process:
            workflow['process'] = related_process
        if related_status:
            workflow['status'] = related_status
        if related_scope:
            workflow['scope'] = related_scope
        if related_wait is not None:
            workflow['wait'] = related_wait

        process_sobj.set_json_value("workflow", workflow)
        self.set_description(process_sobj)
        process_sobj.commit()


    def handle_approval(self):
        pipeline_code = self.kwargs.get("pipeline_code")
        process = self.kwargs.get("process")
        assigned = self.kwargs.get("assigned")

        pipeline = Pipeline.get_by_code(pipeline_code)

        search = Search("config/process")
        search.add_filter("pipeline_code", pipeline_code)
        search.add_filter("process", process)
        process_sobj = search.get_sobject()

        workflow = process_sobj.get_json_value("workflow")
        if not workflow:
            workflow = {}
        if assigned:
            workflow['assigned'] = assigned
        process_sobj.set_json_value("workflow", workflow)
        self.set_description(process_sobj)
        process_sobj.commit()

        cbk_classes = self.kwargs.get("_cbk_classes") or []

        handled = set()
        for cbk_class in cbk_classes:
            if cbk_class in handled:
                continue
            cmd = Common.create_from_class_path(cbk_class, {}, self.kwargs)
            cmd.execute()
            handled.add(cbk_class)


    def handle_status(self):

        pipeline_code = self.kwargs.get("pipeline_code")
        process = self.kwargs.get("process")

        pipeline = Pipeline.get_by_code(pipeline_code)

        search = Search("config/process")
        search.add_filter("pipeline_code", pipeline_code)
        search.add_filter("process", process)
        process_sobj = search.get_sobject()

        if not process_sobj:
            return

        direction = self.kwargs.get("direction")
        status = self.kwargs.get("status")
        mapping = self.kwargs.get("mapping")
        color = self.kwargs.get("color")
        assigned = self.kwargs.get("assigned")

        workflow = process_sobj.get_json_value("workflow")
        if not workflow:
            workflow = {}

        if direction:
            workflow['direction'] = direction
        if status:
            workflow['status'] = status
        if mapping:
            workflow['mapping'] = mapping

        if color:
            process_sobj.set_value("color", color)

        if assigned:
            workflow['assigned'] = assigned

        process_sobj.set_json_value("workflow", workflow)
        self.set_description(process_sobj)
        process_sobj.commit()



    def handle_hierarchy(self):


        pipeline_code = self.kwargs.get("pipeline_code")
        process = self.kwargs.get("process")

        pipeline = Pipeline.get_by_code(pipeline_code)
        search_type = pipeline.get_value("search_type")

        search = Search("config/process")
        search.add_filter("pipeline_code", pipeline_code)
        search.add_filter("process", process)
        process_sobj = search.get_sobject()

        data = process_sobj.get_json_value("workflow") or {}

        subpipeline_code = self.kwargs.get("subpipeline")
        if subpipeline_code:
            process_sobj.set_value("subpipeline_code", subpipeline_code)
        process_sobj.commit()

        task_creation = self.kwargs.get("task_creation") or "subtasks_only"
        data['task_creation'] = task_creation

        process_sobj.set_value("workflow", data)
        self.set_description(process_sobj)
        process_sobj.commit()


    def handle_progress(self):

        pipeline_code = self.kwargs.get("pipeline_code")
        process = self.kwargs.get("process")

        pipeline = Pipeline.get_by_code(pipeline_code)
        search_type = pipeline.get_value("search_type")

        search = Search("config/process")
        search.add_filter("pipeline_code", pipeline_code)
        search.add_filter("process", process)
        process_sobj = search.get_sobject()


        related_search_type = self.kwargs.get("related_search_type")
        related_pipeline_code = self.kwargs.get("related_pipeline_code")
        related_process = self.kwargs.get("related_process")
        if not related_process:
            related_process = process
        related_scope = self.kwargs.get("related_scope")
        if not related_scope:
            related_scope = "local"

        workflow = process_sobj.get_json_value("workflow")
        if not workflow:
            workflow = {}

        if related_search_type:
            workflow['search_type'] = related_search_type
        if related_pipeline_code:
            workflow['pipeline_code'] = related_pipeline_code
        if related_process:
            workflow['process'] = related_process
        if related_scope:
            workflow['scope'] = related_scope


        # find a related trigger
        trigger_code = workflow.get('trigger_code')
        trigger = None
        if trigger_code:
            search = Search("config/trigger")
            search.add_filter("code", trigger_code)
            trigger = search.get_sobject()

        if not trigger:
            trigger = SearchType.create("config/trigger")

        event = "workflow|%s" % (related_search_type)
        trigger.set_value("event", event)

        # update the trigger information
        trigger.set_value("class_name", "pyasm.command.ProcessStatusTrigger")

        # description
        trigger.set_value("description", "Listener for [%s] from [%s]" % (process, search_type))
        trigger.set_value("mode", "same process,same transaction")
        trigger.set_value("process", related_process)

        data = {
                "process_code": process_sobj.get_code(),
                "pipeline_code": pipeline_code,
                "search_type": search_type,
        }
        trigger.set_json_value("data", data)

        trigger.commit()
        trigger_code = trigger.get_code()

        workflow['trigger_code'] = trigger_code


        process_sobj.set_json_value("workflow", workflow)
        self.set_description(process_sobj)
        process_sobj.commit()


class NewProcessInfoCmd(Command):


    def execute(self):
        check_script_execution()

        self.pipeline_code = self.kwargs.get("pipeline_code")
        self.process = self.kwargs.get("process")
        self.pipeline = Pipeline.get_by_code(self.pipeline_code)

        search = Search("config/process")
        search.add_filter("pipeline_code", self.pipeline_code)
        search.add_filter("process", self.process)
        self.process_sobj = search.get_sobject()
        if not self.process_sobj:
            raise LookupError("Process [%s] does not exist in pipeline [%s]" % (self.process, self.pipeline_code))
        self.workflow = self.process_sobj.get_json_value("workflow") or {}

        description = self.kwargs.get("description")
        if description or description == "":
            self.process_sobj.set_value("description", description)

        # custom behavior depending on type
        node_type = self.kwargs.get("node_type")
        if node_type in ["action", "condition"]:
            self.handle_action()
        elif node_type == 'hierarchy':
            self.handle_hierarchy()
        elif node_type == 'progress':
            self.handle_progress()
        elif node_type == 'status':
            self.handle_status()


        # set node workflow data
        workflow = {}
        self.filtered_keys = set(['process', 'pipeline_code', 'None'])
        workflow = self.populate_workflow(workflow, self.kwargs)

        self.process_sobj.set_json_value("workflow", workflow)

        self.process_sobj.commit()

        # custom callback classes
        cbk_classes = self.kwargs.get("_cbk_classes") or []
        handled = set()
        for cbk_class in cbk_classes:
            if cbk_class in handled:
                continue
            cmd = Common.create_from_class_path(cbk_class, {}, self.kwargs)
            cmd.execute()
            handled.add(cbk_class)

        if node_type in ['manual', 'approval', 'action', 'condition', 'hierarchy', 'progress', 'dependency', 'input', 'output']:
            return

        # Get custom save cmd via node_type
        from pyasm.command import CustomProcessConfig
        cmd = CustomProcessConfig.get_save_handler(node_type, self.kwargs)
        if cmd:
            return cmd.execute()



    def populate_workflow(self, workflow, data):

        for key in data:
            value = data.get(key)
            is_empty = value == None or value == ""
            unwanted_keys = key.startswith('_') or key in self.filtered_keys

            if (is_empty or unwanted_keys):
                continue

            if (isinstance(value, dict)):
                value = self.populate_workflow({}, value)

            workflow[key] = value

        return workflow



    def handle_action(self):
        is_admin = Environment.get_security().is_admin()

        action_kwargs = self.kwargs.get("default") or {}
        action = action_kwargs.get("action") or "create_new"
        script = action_kwargs.get("script")
        script_path = action_kwargs.get("script_path")
        on_action_class = action_kwargs.get("on_action_class")
        execute_mode = action_kwargs.get("execute_mode")

        if is_admin:
            language = action_kwargs.get("language")
            if not language:
                language = "python"
        else:
            language = "server_js"

        event = "process|action"

        from tactic.core.process_constants import TRIGGER_FOLDER_PREFIX

        folder = "%s/%s" % (TRIGGER_FOLDER_PREFIX, self.pipeline_code)
        title = self.process_sobj.get_code()

        # check to see if the trigger already exists
        search = Search("config/trigger")
        search.add_filter("event", event)
        search.add_filter("process", self.process_sobj.get_code())
        trigger = search.get_sobject()
        if not trigger:
            # create a new one
            trigger = SearchType.create("config/trigger")
            trigger.set_value("event", event)
            trigger.set_value("process", self.process_sobj.get_code())

        if action == "command":
            trigger.set_value("script_path", "NULL", quoted=False)
            trigger.set_value("class_name", on_action_class)
        else:
            if script_path:
                folder, title = os.path.split(script_path)
            else:
                script_path = "%s/%s" % (folder, title)

            if script or action_kwargs.get("script_path"):
                trigger.set_value("script_path", script_path)
            else:
                trigger.set_value("script_path", "NULL", quoted=False)

            trigger.set_value("class_name", "NULL", quoted=False)

        if execute_mode:
            trigger.set_value("mode", execute_mode)

        trigger.commit()

        if script:
            from pyasm.security import Sudo

            sudo = Sudo()
            try:

                # check to see if the script already exists
                search = Search("config/custom_script")
                search.add_filter("folder", folder)
                search.add_filter("title", "%s" % title)
                script_obj = search.get_sobject()
                if not script_obj:
                    script_obj = SearchType.create("config/custom_script")
                    script_obj.set_value("folder", folder)
                    script_obj.set_value("title", "%s" % title)

                script_obj.set_value("language", language)
                script_obj.set_value("script", script)
                script_obj.commit()

            finally:
                sudo.exit()


    def handle_hierarchy(self):

        hierarchy_kwargs = self.kwargs.get("hierarchy") or {}
        subpipeline_code = hierarchy_kwargs.get("subpipeline")

        if not subpipeline_code:
            default = self.kwargs.get("default")
            if default:
                subpipeline_code = default.get("subpipeline")

        if subpipeline_code:
            self.process_sobj.set_value("subpipeline_code", subpipeline_code)


    def handle_progress(self):

        progress_kwargs = self.kwargs.get("progress") or {}
        search_type = self.pipeline.get_value("search_type")

        related_search_type = progress_kwargs.get("related_search_type")
        related_process = progress_kwargs.get("related_process")
        if not related_process:
            related_process = progress_kwargs['related_process'] = self.process
        related_scope = progress_kwargs.get("related_scope")
        if not related_scope:
            progress_kwargs['related_scope'] = "local"

        # find a related trigger
        old_kwargs = self.workflow.get("progress") or {}
        trigger_code = old_kwargs.get('trigger_code')
        trigger = None
        if trigger_code:
            search = Search("config/trigger")
            search.add_filter("code", trigger_code)
            trigger = search.get_sobject()

        if not trigger:
            trigger = SearchType.create("config/trigger")

        event = "workflow|%s" % (related_search_type)
        trigger.set_value("event", event)

        # update the trigger information
        trigger.set_value("class_name", "pyasm.command.ProcessStatusTrigger")

        # description
        trigger.set_value("description", "Listener for [%s] from [%s]" % (self.process, search_type))
        trigger.set_value("mode", "same process,same transaction")
        trigger.set_value("process", related_process)

        data = {
                "process_code": self.process_sobj.get_code(),
                "pipeline_code": self.pipeline_code,
                "search_type": search_type,
        }
        trigger.set_json_value("data", data)
        trigger.commit()

        trigger_code = trigger.get_code()
        progress_kwargs['trigger_code'] = trigger_code

        self.kwargs['progress'] = progress_kwargs


    def handle_status(self):

        status_kwargs = self.kwargs.get("default") or {}

        color = status_kwargs.get("color")
        if color:
            self.process_sobj.set_value("color", color)

        mapping = status_kwargs.get("mapping")
        if mapping:
            self.kwargs['mapping'] = mapping

        direction = status_kwargs.get("direction")
        if direction:
            self.kwargs['direction'] = direction

        status = status_kwargs.get("status")
        if status:
            self.kwargs['status'] = status

