###########################################################
#
# Copyright (c) 2010, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#
__all__ = [
    'PipelineTaskStatusTrigger', 'PipelineTaskTrigger', 'PipelineTaskDateTrigger',
    'PipelineTaskCreateTrigger', 'RelatedTaskUpdateTrigger', 'TaskCreatorTrigger',
    'TaskCompleteTrigger', 'PipelineParentStatusTrigger',
]

from pyasm.common import Common, jsonloads, Container, TacticException
from pyasm.command import Trigger
from pyasm.security import Sudo
from pyasm.biz import Pipeline, Task
from pyasm.search import Search, SObject, SearchKey


class PipelineTaskStatusTrigger(Trigger):
    SAMPLE_DATA = {
        'src_process': 'ingest',
        'src_status': 'Approved',
        'dst_process': 'work',
        'dst_status': 'Pending',
    }

    def execute(self):
        trigger_sobj = self.get_trigger_sobj()
        data = trigger_sobj.get_value("data")
        data = jsonloads(data) if data else {}

        data_list = data if isinstance(data, list) else [data]
        caller = self.get_caller()
        for data in data_list:
            if not isinstance(data, dict):
                continue
            src_task = caller
            if not isinstance(src_task, SObject):
                input = self.get_input()
                snapshot = input.get('snapshot')
                if not snapshot:
                    continue
                if isinstance(snapshot, dict):
                    snapshot = SearchKey.get_by_search_key(snapshot.get('__search_key__'))
                src_process = data.get('src_process')
                src_task = Search.eval(
                    "@SOBJECT(parent.sthpw/task['process','%s'])" % src_process,
                    sobjects=snapshot, single=True,
                )
                if not src_task:
                    continue

            src_process = data.get("src_process")
            if src_process and src_task.get_value("process") != src_process:
                continue

            src_status = data.get("src_status")
            if src_status and src_task.get_value("status") != src_status:
                continue

            script_path = trigger_sobj.get_value("script_path")
            if script_path:
                from tactic.command import PythonTrigger
                cmd = PythonTrigger(script_path=script_path)
                cmd.set_trigger_sobj(trigger_sobj)
                cmd.set_caller(caller)
                cmd.set_event(self.get_event())
                cmd.set_input(self.input)
                cmd.set_output(self.input)
                cmd.execute()
                continue

            class_path = data.get("class_path")
            if class_path:
                trigger = Common.create_from_class_path(class_path)
                if isinstance(trigger, Trigger):
                    trigger.set_trigger_sobj(trigger_sobj)
                    trigger.set_caller(caller)
                trigger.set_event(self.get_event())
                trigger.set_input(self.input)
                trigger.set_output(self.input)
                trigger.execute()
                continue

            dst_process = data.get("dst_process")
            dst_status = data.get("dst_status")

            sobject = src_task.get_parent()
            if not sobject:
                continue
            tasks = Task.get_by_sobject(sobject)

            updated_tasks = []
            use_parent = data.get("use_parent")
            if use_parent in [True, 'true']:
                parent = sobject.get_parent()
                if not parent:
                    continue
                parent_tasks = Task.get_by_sobject(parent, dst_process)

                condition = data.get("condition") or "all"
                condition_met = False

                if condition == "all":
                    relevant = [t for t in tasks if not src_process or t.get_value("process") == src_process] or tasks
                    condition_met = all(task.get_value("status") == src_status for task in relevant)
                elif condition == "any":
                    for task in tasks:
                        if task.get_value("status") == src_status:
                            condition_met = True
                            break

                if condition_met:
                    for task in parent_tasks:
                        if task.get_value("process") == dst_process:
                            updated_tasks.append(task)
            else:
                for task in tasks:
                    if task.get_value("process") == dst_process:
                        updated_tasks.append(task)

            for task in updated_tasks:
                if task.get_value("process") == dst_process:
                    task.set_value("status", dst_status)
                    task.commit()


class PipelineTaskTrigger(Trigger):
    '''This is the trigger that is executed on a change'''

    ARGS_KEYS = {}

    def execute(self):
        trigger_sobj = self.get_trigger_sobj()
        data = trigger_sobj.get_value("data")
        data = jsonloads(data) if data else []
        from tactic.ui.filter import FilterData
        filter_data = FilterData(data)

        task = self.get_caller()

        trigger_info = filter_data.get_values_by_index("trigger")
        process = trigger_info.get("process")

        if task.get_value("process") != process:
            return

        parent = None
        rules = filter_data.get_values_by_prefix("rule")

        is_valid = True
        for rule in rules:
            attribute = rule.get('name')
            value = rule.get('value')

            if attribute in ['status']:
                if task.get_value(attribute) != value:
                    is_valid = False
            elif attribute in ['pipeline']:
                attribute = 'pipeline_code'
                if parent is None:
                    parent = task.get_parent()
                    if parent is None:
                        continue
                if parent.get_value(attribute) != value:
                    is_valid = False
            else:
                is_valid = False

        if not is_valid:
            return

        output_tasks = task.get_output_tasks()
        input_tasks = task.get_input_tasks()
        actions = filter_data.get_values_by_prefix("action")

        for action in actions:
            type = action.get("type")
            attribute = action.get('name')
            value = action.get('value')

            if type in ('output', 'input'):
                for output_task in output_tasks:
                    output_task.set_value(attribute, value)
                    output_task.commit()
            elif type == 'process':
                process = action.get("process")
                for input_task in input_tasks:
                    if input_task.get_value("process") == process:
                        input_task.set_value(attribute, value)
                        input_task.commit()
                        break
                for output_task in output_tasks:
                    if output_task.get_value("process") == process:
                        output_task.set_value(attribute, value)
                        output_task.commit()
                        break


class PipelineParentStatusTrigger(Trigger):
    '''This is the trigger that is executed on a change'''

    ARGS_KEYS = {}

    def execute(self):
        trigger_sobj = self.get_trigger_sobj()
        data = trigger_sobj.get_value("data")
        data = jsonloads(data) if data else {}

        dst_status = data.get('dst_status')
        item = self.get_caller()

        parent = item.get_parent()
        if not parent:
            return

        parent.set_value("status", dst_status)
        parent.commit()


class PipelineTaskDateTrigger(Trigger):
    '''This is the trigger that is executed on a change'''

    ARGS_KEYS = {}

    def execute(self):
        trigger_sobj = self.get_trigger_sobj()
        data = trigger_sobj.get_value("data")
        data = jsonloads(data) if data else {}

        column = data.get('column')
        src_status = data.get('src_status')

        item = self.get_caller()

        if isinstance(item, SObject):
            if isinstance(item, Task):
                if src_status is not None:
                    if item.get_value("status") != src_status:
                        return
                item.set_now(column)
                item.commit()
            else:
                process = item.get_value('process')
                expr = '@SOBJECT(parent.sthpw/task["process","%s"])' % process
                tasks = Search.eval(expr, sobjects=[item])
                if tasks:
                    for task in tasks:
                        task.set_now(column)
                        task.commit()
        else:
            if hasattr(item, 'process'):
                process = item.process
                expr = '@SOBJECT(sthpw/task["process","%s"])' % process
                tasks = Search.eval(expr, sobjects=[item.sobject])
                if tasks:
                    for task in tasks:
                        task.set_now(column)
                        task.commit()


class RelatedTaskUpdateTrigger(Trigger):
    '''This is called on every task change.  It syncronizes tasks with
    the same context'''
    def execute(self):
        return


class PipelineTaskCreateTrigger(Trigger):

    def execute(self):
        input = self.get_input()

        search_key = input.get("search_key")
        task = Search.get_by_search_key(search_key) if search_key else self.get_caller()
        parent = task.get_parent() if task else None
        if not parent:
            raise TacticException("Task parent not found.")

        trigger_sobj = self.get_trigger_sobj()
        data = trigger_sobj.get_value("data")
        try:
            data = jsonloads(data)
        except Exception:
            raise TacticException("Incorrect formatting of trigger [%s]." % trigger_sobj.get_value("code"))

        src_status = data.get("src_status")
        if src_status:
            task_status = task.get_value("status")
            if task_status != src_status:
                return

        process_names = data.get("output")
        if not process_names:
            return

        Task.add_initial_tasks(parent, parent.get_value('pipeline_code'), processes=process_names,
                               contexts=process_names, skip_duplicate=True, mode='standard', start_offset=0)


class TaskCreatorTrigger(Trigger):
    '''This is executed on every insert of an sobject'''

    def has_been_called(self, prev_called_triggers):
        return False

    def execute(self):
        input = self.get_input()

        search_key = input.get("search_key")
        update_data = input.get("update_data")

        if not search_key or search_key.startswith('sthpw/'):
            return

        mode = input.get("mode")
        if mode not in ['insert']:
            return

        sobject = self.get_caller()
        pipeline_code = sobject.get_value("pipeline_code", no_exception=True)

        if not pipeline_code:
            return

        from pyasm.biz import Pipeline, Task

        try:
            pipeline = Pipeline.get_by_code(pipeline_code)
        except Exception:
            pipeline = None

        if not pipeline:
            return

        if pipeline.get_value("autocreate_tasks", no_exception=True) not in ['true', True]:
            return

        Task.add_initial_tasks(sobject, pipeline_code=pipeline_code, skip_duplicate=True, mode='standard')


class TaskCompleteTrigger(Trigger):
    '''This trigger is executed to state "officially" that the task is complete'''
    def execute(self):
        input = self.get_input()
        sobject = self.get_caller()

        if isinstance(sobject, Task):
            task = sobject
        else:
            process = input.get("process")
            raise Exception("Not supported yet")

        process = task.get_value("process")
        status = task.get_value("status")

        pipeline_code = task.get_value("pipeline_code")
        if not pipeline_code:
            pipeline_code = 'task'

        task_pipeline = Pipeline.get_by_code(pipeline_code)
        if not task_pipeline:
            return
        statuses = task_pipeline.get_process_names()
        if not statuses:
            return

        completion_statuses = []
        for status in statuses:
            status_obj = task_pipeline.get_process(status)
            attrs = status_obj.get_attributes()
            completion = attrs.get("completion")
            if completion == "100":
                completion_statuses.append(status)

        if not completion_statuses:
            completion_statuses.append(statuses[-1])

        is_complete = False

        update_data = input.get('update_data')
        if update_data.get("status") in completion_statuses:
            is_complete = True

        if is_complete == True:
            if not task.get_value("actual_end_date"):
                task.set_now("actual_end_date")
                self.add_description('Internal Task Complete Trigger')
                task.commit(triggers=False)
