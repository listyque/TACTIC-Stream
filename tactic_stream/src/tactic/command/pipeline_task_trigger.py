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

# Selected complete class; the other handlers need unported Task/UI dependencies.
from pyasm.command import Trigger


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
        from pyasm.search import SearchType

        try:
            pipeline = Pipeline.get_by_code(pipeline_code)
        except:
            # if pipeline does not exist
            pipeline = None

        if not pipeline:
            return

        if pipeline.get_value("autocreate_tasks", no_exception=True) not in ['true', True]:
            return

        #import time
        #start = time.time()
        Task.add_initial_tasks(sobject, pipeline_code=pipeline_code, skip_duplicate=True, mode='standard')

from pyasm.biz import Task, Pipeline


class RelatedTaskUpdateTrigger(Trigger):
    '''This is called on every task change.  It syncronizes tasks with
    the same context'''
    def execute(self):

        # DISABLING this ... this is a rather tenuous trigger that attempts to allow for
        # tasks to be "connected" to each other in a way that makes it look like you have
        # multiple people assigned to a task.  While this may be desireable, the mechanism
        # used below checks for the same process and context to identify tasks tat are connected.
        # This is too broad and should be done more explicitly rather than implicitly
        return

        sudo = Sudo()

        input = self.get_input()
        search_key = input.get("search_key")
        update_data = input.get("update_data")
        mode = input.get("mode")
        if mode in ['insert','delete','retire']:
            return

        task = Search.get_by_search_key(search_key)

        process = task.get_value("process")
        context = task.get_value("context")
        parent = task.get_parent()


        # find all of the tasks with the same parent and same context
        search = Search("sthpw/task")
        search.add_parent_filter(parent)
        search.add_filter("process", process)
        search.add_filter("context", context)
        tasks = search.get_sobjects()

        trigger_dict = Container.get('RelatedTaskUpdateTrigger')
        if not trigger_dict:
            trigger_dict = {}

        for attr, value in update_data.items():
            # skip assigned as this is the only difference between related tasks
            if attr == 'assigned':
                continue
            # update_data could have the post-conversion value None
            if value == None:
                value = ''

            for task in tasks:
                task_search_key = task.get_search_key()
                # skip the current one
                if task_search_key == search_key or trigger_dict.get(task_search_key):
                    continue
                task.set_value(attr, value)
                trigger_dict[task_search_key] = True
                Container.put('RelatedTaskUpdateTrigger', trigger_dict)
                # this should run trigger where applicable
                task.commit(triggers=True)

        del sudo


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



        # get the task process
        process = task.get_value("process")
        status = task.get_value("status")


        pipeline_code = task.get_value("pipeline_code")
        if not pipeline_code:
            pipeline_code = 'task'

        task_pipeline = Pipeline.get_by_code(pipeline_code)
        if not task_pipeline:
            return
        # get the last process
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
            #task.set_value("is_complete", True)
            if not task.get_value("actual_end_date"):
                task.set_now("actual_end_date")
                self.add_description('Internal Task Complete Trigger')
                task.commit(triggers=False)
