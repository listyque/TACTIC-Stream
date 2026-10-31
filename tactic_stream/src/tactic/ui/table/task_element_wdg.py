###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

"""Native task selection/column metadata; legacy DOM rendering is excluded."""
import functools
import json
import re
import six
from pyasm.common import Environment, TacticException, SecurityException
from pyasm.command.edit_wdg_action import DatabaseAction
from pyasm.common.errors import UnsupportedContract
from pyasm.biz import Pipeline, Project, Task, Schema
from pyasm.search import Search, SearchType, SObject
from tactic.ui.common import BaseTableElementWdg
__all__ = ['TaskElementWdg', 'TaskElementCbk', 'WorkElementWdg']

basestring = six.string_types

def cmp(a, b):
    return (a > b) - (a < b)

def get_compare(processes):
    def compare(a,b):
        a_process = a.get_value('process')
        b_process = b.get_value('process')
        
        try:
            a_index = processes.index(a_process)
        except ValueError:
            a_index = -1
        try:
            b_index = processes.index(b_process)
        except ValueError:
            b_index = -1

        if a_index > -1 and b_index > -1:
            if a_index == b_index:
                # compare context if process is the same
                a_context = a.get_value('context')
                b_context = b.get_value('context')
                return cmp(a_context, b_context)
            else:
                return cmp(a_index, b_index)

        # handle cases where process is not in pipeline
        if a_index == -1 and b_index == -1:
            return cmp(a_process, b_process)
        elif a_index != -1:
            return -1
        elif b_index != -1:
            return 1

    return functools.cmp_to_key(compare)

class TaskElementWdg(BaseTableElementWdg):
    relationship_type = None
    LAYOUT_WIDTH = 130

    ARGS_KEYS = {
    'layout': {
        'description': 'Determines layout for each process',
        'type': 'SelectWdg',
        'values': 'panel|vertical|horizontal',
        'category': 'Mode',
        'order': '01'
    },

    'show_filler_tasks': {
        'description': 'Flag to determine filler tasks are shown dynamically',
        'type': 'SelectWdg',
        'values': 'true|false',
        'category': 'Mode',
        'order': '02'
    },

    'edit_status': {
        'description': 'Flag to determine whether the status is editable',
        'type': 'SelectWdg',
        'values': 'true|false',
        'category': 'Mode',
        'order': '03'
    },
    'edit_assigned': {
        'description': 'Flag for editing the assigned user of the tasks',
        'type': 'SelectWdg',
        'values': 'true|false',
        'category': 'Mode',
        'order': '04',
    },

    'show_labels': {
        'description': 'Flag for displaying the label of the tasks',
        'type': 'SelectWdg',
        'values': 'true|false',
        'category': 'Display',
        'order': '15'
    },

    'show_border': {
        'description': 'Flag for displaying a border around each task panel',
        'type': 'SelectWdg',
        'values': 'all|one-sided|none',
        'category': 'Display',
        'order': '16'
    },

    'bg_color': {
        'description': 'Different modes of displaying the background color for each process',
        'type': 'SelectWdg',
        'values': 'status|process',
        'order': '02',
        'category': "Color"
    },

    'status_color': {
        'description': 'Different modes of displaying status background color',
        'type': 'SelectWdg',
        'values': 'status|process',
        'order': '03',
        'category': "Color"
    },
    'context_color': {
        'description': 'Different modes of displaying context background color',
        'type': 'SelectWdg',
        'values': 'status|process',
        'order': '04',
        'category': "Color"
    },
    'panel_width': {
        'description': 'Select the overall width for the panel layout',
        'type': 'SelectWdg',
        'values': '35px|50px|75px|100px|125px',
        'empty': 'true',
        'category': 'Display',
        'order': '06'
    },
    'font_size': {
        'description': 'font size of the text',
        'type': 'SelectWdg',
        'values': '7|8|9|10|11|12|13|14',
        'category': 'Display',
        'empty': 'true',
        'order': '07'
    },

    'show_process': {
        'description': 'Flag for displaying the process of the tasks',
        'type': 'SelectWdg',
        'values': 'true|false',
        'order': '08',
        'category': "Display"
    },
    'show_context': {
        'description': 'Flag for displaying the context of the tasks',
        'type': 'SelectWdg',
        'values': 'true|false',
        'order': '09',
        'category': 'Display'
    },

    'show_status': {
        'description': 'Flag for displaying the status of the tasks',
        'type': 'SelectWdg',
        'values': 'true|false',
        'order': '10',
        'category': 'Display'
    },

    'show_assigned': {
        'description': 'Flag for displaying the assigned user of the tasks',
        'type': 'SelectWdg',
        'values': 'true|false',
        'order': '10',
        'category': 'Display'
    },

    'show_bid': {
        'description': 'Flag for displaying the bid duration tasks',
        'type': 'SelectWdg',
        'values': 'true|false',
        'order': '10',
        'category': 'Display'
    },

    'assigned_label_attr': {
        'description': 'A list of | separated attributes displayed as the label of the assigned, e.g. "first_name|last_name"',
        'type': 'TextWdg',
        'order': '11',
        'category': 'Display'
    },

    'assigned_values_expr': {
        'description': '''An expression controlling what login values to show, e.g. @SOBJECT(sthpw/login['department','design'])''',
        'type': 'TextWdg',
        'order': '12',
        'category': 'Display'
    },

    'show_dates': {
        'description': 'Flag for displaying the date range of the tasks',
        'type': 'SelectWdg',
        'values': 'true|false',
        'order': '13',
        'category': 'Display',
    },

    'show_task_edit': {
        'description': 'Flag for displaying the edit icon for each task',
        'type': 'SelectWdg',
        'values': 'true|false',
        'order': '22',
        'category': 'Display',
    },

    'task_edit_view': {
        'description': 'A custom view specified for editing the task in this widget. Defaults to edit',
        'type': 'TextWdg',
        'default': 'edit',
        'category': 'Display',
        'order': '23'
    },

    'show_add_task': {
        'description': 'Flag for displaying the add task button even if there are existing tasks. Defaults to false',
        'type': 'SelectWdg',
        'values': 'true|false',
        'category': 'Display',
        'order': '19'
    },

    'show_link_task_menu': {
        'description': 'Flag for displaying the task linking menu so one can virtually make a task shared by two or more people. Defaults to false',
        'type': 'SelectWdg',
        'values': 'true|false',
        'category': 'Display',
        'order': '20'
    },

    'show_processes_in_title': {
        'description': 'Display the processes in title. You are advised to turn on show_filler_tasks as well. Defaults to false',
        'type': 'SelectWdg',
        'values': 'true|false',
        'category': 'Display',
        'order': '21'
    },

    'task_filter': {
        'description': 'A filter on which type of tasks to display',
        'type': 'SelectWdg',
        'values': 'process_only|context_only',
        'category': 'Display',
        'order': '24'
    },

    'show_track': {
        'description': 'Flag for displaying a tip to dynamically load the information of the last status',
        'type': 'SelectWdg',
        'values': 'true|false',
        'order': '14',
        'category': 'Display',
    },

    'show_current_pipeline_only': {
        'description': 'Flag for displaying only the tasks associate with the current pipeline. Default to true.',
        'type': 'SelectWdg',
        'values': 'true|false',
        'category': 'Display',
        'order': '18'
    },
    'collate_columns': {
        'description': 'Flag to collate columns that have the same processes together .',
        'type': 'SelectWdg',
        'values': 'true|false',
        'category': 'Display',
        'order': '18'
    }

    }

    def init(self):
        self.label_dict = {}
        self.status_colors = {}
        self.process_colors = {}
        self._startup_tips = False
        self.tasks_dict = {}
        self.permission = {}
        self.identities = {}

        self.filler_cache = None
        self.sorted_processes = []

    def get_width(self):
        if self.sobjects:
            #sobject = self.sobjects[0]
            pipeline_code = self.get_pipeline_code()
            pipeline = Pipeline.get_by_code(pipeline_code)
            if not pipeline:
                pipeline = Pipeline.get_by_code("task")
            processes = pipeline.get_process_names()
            return 120 * len(processes) + 10
        else:
            return 400

    @classmethod
    def is_editable(cls):
        '''to avoid all those CellEditWdg'''
        return False

    def get_searchable_search_type(self):
        '''get the searchable SType for local search'''
        return 'sthpw/task'

    def get_pipeline_code(self):
        pipeline_code = self.kwargs.get("pipeline_code")

        if not pipeline_code:
            sobject = self.get_current_sobject()
            pipeline_code = sobject.get_value("pipeline_code", no_exception=True)

        return pipeline_code.replace('$PROJECT', Project.get_project_code()) if pipeline_code else ''

    def get_text_value(self):
        tasks = self.get_tasks()
    
        values = []
        for task in tasks:
            group = []
            group.append(task.get_value('context'))
            group.append(task.get_value('status'))
            group.append(task.get_value('assigned'))
            values.append(':'.join(group))
        return ",".join(values)

    def _get_display_options(self):
       
        # this is used only for horizontal layout
        # NOTE: total_width is no longer used
        self.total_width = 0
        self.panel_width = self.kwargs.get("panel_width")
        self.show_border = self.kwargs.get("show_border")
        self.show_process = self.kwargs.get("show_process")
        self.show_context = self.kwargs.get("show_context")
        self.show_task_edit = self.kwargs.get("show_task_edit")
        self.task_edit_view = self.kwargs.get("task_edit_view")

        self.show_processes_in_title = self.kwargs.get("show_processes_in_title")
        if not self.show_processes_in_title:
            self.show_processes_in_title = 'false'

        if not self.show_process:
            self.show_process = 'true'
        if not self.show_context:
            self.show_context = 'false'

        if not self.show_task_edit:
            self.show_task_edit = 'false'
        if not self.task_edit_view:
            self.task_edit_view = 'edit'

        self.show_dates = self.kwargs.get("show_dates")
        if not self.show_dates:
            self.show_dates = "true"

        self.show_status = self.kwargs.get("show_status")
        if not self.show_status:
            self.show_status = "true"
        self.show_assigned = self.kwargs.get("show_assigned")
        if not self.show_assigned:
            self.show_assigned = "true"
        self.edit_assigned = self.kwargs.get("edit_assigned")
        if not self.edit_assigned:
            self.edit_assigned = "false"

        self.text_color = self.kwargs.get('text_color')

        if not self.show_border:
            self.show_border = 'one-sided'
        
        self.show_labels = self.kwargs.get("show_labels")
        self.show_track = self.kwargs.get("show_track")
        self.show_add_task = self.kwargs.get("show_add_task") == 'true'
        self.show_link_task_menu = self.kwargs.get("show_link_task_menu") == 'true'
       
        # handle the color
        self.status_color_mode = self.kwargs.get("status_color")
        self.context_color_mode = self.kwargs.get("context_color")
        self.bg_color_mode = self.kwargs.get("bg_color")
        '''
        if not status_color_mode:
            status_color_mode = 'status'
        if not context_color_mode:
            context_color_mode = 'process'
        '''

        if not self.show_labels:
            self.show_labels = 'false'

        self.font_size = self.kwargs.get("font_size")
        if not self.font_size:
            self.font_size = 12
        else:
            self.font_size = int(self.font_size)

        self.edit_status = self.kwargs.get("edit_status") == 'true'
        self.layout = self.kwargs.get("layout")
        if not self.layout:
            self.layout = 'panel'
        if self.layout in ['horizontal','vertical']:
            if self.show_process =='true':
                if self.layout == 'vertical':
                    self.total_width += self.LAYOUT_WIDTH
                else:
                    self.total_width += 75

            if self.show_context =='true':
                self.total_width += 75 
            if self.show_dates =='true':
                if self.layout == 'vertical':
                    self.total_width += self.LAYOUT_WIDTH
                elif self.font_size < 10:
                    self.total_width += 50
                else:
                    self.total_width += 75 

            if self.show_assigned == 'true':
                if self.show_task_edit == 'true':
                    self.total_width += 250
                else:
                    self.total_width += 120
            if self.show_labels =='true':
                self.total_width += 75 
            if self.show_track =='true':
                self.total_width += 25
            # editable select takes more width
            if self.show_status == 'true':
                if self.edit_status:
                    self.total_width += 100
                else:
                    self.total_width += 75

        self.task_filter = self.kwargs.get('task_filter')

    def check_access(self):
        '''check access for each element'''

        project_code = Project.get_project_code() 
        security = Environment.get_security()
        
        element_names = ['assigned','status']
        search_type = 'sthpw/task'
        for element_name in element_names:

            def_default_access = 'edit'

            # check security access
            access_key2 = {
                'search_type': search_type,
                'project': project_code
            }
            access_key1 = {
                'search_type': search_type,
                'key': element_name, 
                'project': project_code

            }
            access_keys = [access_key1, access_key2]
            is_viewable = security.check_access('element', access_keys, "view", default=def_default_access)
            is_editable = security.check_access('element', access_keys, "edit", default=def_default_access)
            self.permission[element_name] = {'is_viewable': is_viewable, 'is_editable': is_editable}

    def preprocess(self):

        self.init()
        self._get_display_options()
        self._prepared = False
        self.pipelines_dict = {}
        if not self.sobjects:
            self._prepared = True
            return

        self.assignee = []
        self.assignee_labels = []
        self.assignee_dict = {}

        self.check_access()

        # deals with assignee labels if provided
        assigned = self.kwargs.get('edit_assigned')
        self.assigned_label = None
        # e.g. first_name|last_name
        self.assigned_label_attr = self.kwargs.get('assigned_label_attr')
        self.assigned_values_expr = self.kwargs.get('assigned_values_expr')
        if not self.assigned_values_expr:
            self.assigned_values_expr = "@SOBJECT(sthpw/login['@ORDER_BY','display_name'])"

        if assigned == 'true':
            if self.assigned_label_attr:
                users = Search.eval(self.assigned_values_expr)
                user_names = [x.get_value('login') for x in users]
                self.assigned_label_attr = self.assigned_label_attr.split('|')
                self.assigned_label = [x.strip() for x in self.assigned_label_attr if x]

                if self.assigned_label:
                    for user in users:
                        user_labels = [user.get_value(x) for x in self.assigned_label]
                        label = ' '.join(user_labels)
                        self.assignee_labels.append(label)
                        self.assignee_dict[user.get_value('login')] = label
                
            else:
                users = Search.eval(self.assigned_values_expr)
                user_names = SObject.get_values(users, 'login')
                display_names = SObject.get_values(users, 'display_name')
                self.assignee_labels = display_names

            self.assignee = user_names
        else:
            if self.assigned_label_attr:
                users = Search.eval(self.assigned_values_expr)
                self.assigned_label_attr = self.assigned_label_attr.split('|')
                self.assigned_label = [x.strip() for x in self.assigned_label_attr if x]

                if self.assigned_label:
                    for user in users:
                        user_labels = [user.get_value(x) for x in self.assigned_label]
                        label = ' '.join(user_labels)
                        self.assignee_labels.append(label)
                        self.assignee_dict[user.get_value('login')] = label

        self.tasks_dict = {}

        expression = self.kwargs.get("expression")
        if expression:
            self.tasks_dict = Search.eval(expression, self.sobjects, dictionary=True)
        else: 
            # get all of the tasks for all of the sobjects
            search = Search("sthpw/task")
            search.add_relationship_filters(self.sobjects, type=self.relationship_type)

            # this serves a shortcut to limit what context to show
            context = self.kwargs.get("context")
            if context:
                contexts = context.split("|")
                search.add_filters("context", contexts)

            # this serves a shortcut to limit what processes to show
            process = self.kwargs.get("process")
            if process:
                processes = process.split("|")

                search.add_filters("process", processes)

            # go thru children of main search
            search = self.alter_task_search(search, prefix='children')
            search.add_order_by("id")
            tasks = search.get_sobjects()

            schema = Schema.get()

            # process the tasks
            for task in tasks:
                search_type = SearchType.build_search_type(task.get_value("search_type"), task.get_value("project_code"))

                supprocess = self.kwargs.get("parent_process")
                if supprocess:
                    process = task.get_value("process")
                    if not process.startswith("%s." % supprocess):
                        continue

                attrs = schema.get_relationship_attrs("sthpw/task", search_type, type=self.relationship_type)
                attrs = schema.resolve_relationship_attrs(attrs, "sthpw/task", search_type)
                from_col = attrs.get("from_col")

                code = task.get_value(from_col)
                key = "%s|%s" % (search_type, code)

                tasks_list = self.tasks_dict.get(key)
                if tasks_list == None:
                    tasks_list = []
                    self.tasks_dict[key] = tasks_list

                tasks_list.append(task)

        pipeline_code = self.kwargs.get("pipeline_code")
        if pipeline_code:
            pipeline_codes = [pipeline_code]
        else:
            pipeline_codes = SObject.get_values(self.sobjects, 'pipeline_code', unique=True, no_exception=True)

        # pipeline_codes can have an item that is something like $PROJECT/shot.
        # when this happens, in the eval, $PROJECT is replaced by something like 'vfx'
        # because there are quotes around it, it messes up the expression 
        # So, replace $PROJECT here, and thus, getting rid of the code
        project_code = Project.get_project_code()

        if pipeline_codes:
            # prevent expression error
            pipeline_codes = [ x.replace('$PROJECT', project_code) for x in pipeline_codes ]

        pipelines = Search.eval("@SOBJECT(sthpw/pipeline['code','in','%s'])" % '|'.join(pipeline_codes) )

        # remember the pipelines by code
        self.pipelines_dict = {}
        for pipeline in pipelines:
            self.pipelines_dict[pipeline.get_code()] = pipeline

        # get all of the processes that appear in all the pipelines, without duplicates
        self.all_processes_set = set()
        # ^ that's what the pipeline column should display (each process in the pipeline)

        # the default pipeline is the longest pipeline in the table
        # this is so that the processes appear in the right order.
        # all other processes should follow after this
        default_pipeline = []

        if pipelines:
            for pipeline in pipelines:
                processes = pipeline.get_processes(type=[
                        #"node",
                        "manual",
                        "approval",
                        "hierarchy",
                        #"dependency",
                        "progress"
                ])

                # if this pipeline has more processes than the default, make this the default
                if len(processes) > len(default_pipeline):
                    default_pipeline = processes
                pipeline_code = pipeline.get_code()
                self.label_dict[pipeline_code] = {}
                for process in processes:
                    # put the processes found into a set to avoid duplicates.
                    self.all_processes_set.add(process.get_name())
                    process_dict = self.label_dict.get(pipeline_code)
                    process_dict[process.get_name()] = process.get_label() 

            # sort the processes, so that the task appears in the right order
            default_pipeline_processes = []

            # get an list of all the processes, in order
            default_pipeline_processes = [x.get_name() for x in default_pipeline]

            # this will add every process in default pipeline to sorted processes 
            # (in the correct order)
            for item in default_pipeline_processes:
                for process in self.all_processes_set:
                    if item == process:
                        self.sorted_processes.append(item)

            # add everything else not in the default pipeline after
            for process in self.all_processes_set:
                if process not in self.sorted_processes:
                    self.sorted_processes.append(process)

        # get all of the assigned logins for each process
        self.assigned_login_groups = {}
        for pipeline in pipelines:
            for process in pipeline.get_processes():
                assigned_login_group = process.get_attribute("assigned_login_group")

                if not assigned_login_group:
                    continue

                key = "%s|%s" % (pipeline.get_code(), process.get_name())
                exists = self.assigned_login_groups.get(key)
                if exists is None:
                    # First, search the login_in_group table for the members in the group.
                    search = Search("sthpw/login_in_group")
                    search.add_filter("login_group", assigned_login_group)

                    # We then need to search the login table for the logins.
                    search_login = Search("sthpw/login")
                    search_login.add_relationship_search_filter(search)
                    users = search_login.get_sobjects()

                    if users:
                        users = [x.get("login") for x in users]
                    else:
                        users = []
                    self.assigned_login_groups[key] = users

        self.assigned_login_groups_labels = {}
        for value, label in zip(self.assignee, self.assignee_labels):
            self.assigned_login_groups_labels[value] = label

        task_pipelines = Search.eval("@SOBJECT(sthpw/pipeline['search_type','sthpw/task'])")
        task_pipelines.append( Pipeline.get_by_code("task") )
        task_pipelines.append( Pipeline.get_by_code("approval") )
        task_pipelines.append( Pipeline.get_by_code("progress") )
        task_pipelines = [pipeline for pipeline in task_pipelines if pipeline]
        if task_pipelines:
            for task_pipeline in task_pipelines:
                processes = task_pipeline.get_processes()
                pipeline_code = task_pipeline.get_code()
                self.status_colors[pipeline_code] = {}
                for process in processes:
                    process_dict = self.status_colors.get(pipeline_code)
                    color = process.get_color()
                    #if color:
                    process_dict[process.get_name()] = color
       
        # ensured all status_colors are filled with by cascading to task or
        # default built in color
        for task_pipeline in task_pipelines:
            task_pipeline_code = task_pipeline.get_code()
            status_colors = self.status_colors.get(task_pipeline_code)
            if status_colors:
                for key, value in status_colors.items():
                    color = value
                    if not color:
                        task_status_colors = self.status_colors.get("task")
                        color = (task_status_colors or {}).get(key)
                    if not color:
                        color = Task.get_default_color(key)
                    status_colors[key] = color

        security = Environment.get_security()
        self.allowed_statuses = []
        for pipeline_code, color_dict in self.status_colors.items():
            existing_statuses = color_dict.keys()
            # check security access

            for status in existing_statuses:
                if status in self.allowed_statuses:
                    continue
                
                access_key = [
                    {'process': '*' ,'pipeline':  pipeline_code},
                    {'process': '*' ,'pipeline':  '*'},
                    {'process': status , 'pipeline':  pipeline_code}
                    ]
                if security.check_access('process', access_key, "view", default="deny"):
                    self.allowed_statuses.append(status)

        if self.sobjects:
            # these are the items in the table being displayed. ie: shots in shot table
            search_type = self.sobjects[0].get_base_search_type()
            if search_type:
                sobj_pipelines = Search.eval("@SOBJECT(sthpw/pipeline['search_type','%s'])" %search_type)
                if sobj_pipelines:
                    for sobj_pipeline in sobj_pipelines:
                        processes = sobj_pipeline.get_processes()
                        pipeline_code = sobj_pipeline.get_code()
                        self.process_colors[pipeline_code] = {}
                        for process in processes:
                            process_dict = self.process_colors.get(pipeline_code)
                            process_dict[process.get_name()] = process.get_color()
        from tactic_stream.server.security_groups import user_identities
        logins = {task.get_value('assigned') for tasks in self.tasks_dict.values() for task in tasks if task.get_value('assigned')}
        self.identities = {}
        if logins:
            users = Search('sthpw/login'); users.set_show_retired(True); users.add_filters('login', list(logins))
            self.identities = {user['login']: user for user in user_identities(users.get_sobjects())}
        self._prepared = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.init()
        self._prepared = False

    def set_sobjects(self, sobjects, search=None):
        super().set_sobjects(sobjects, search)
        self._prepared = False

    def set_options(self, options):
        super().set_options(options)
        self.kwargs.update(options)
        self._prepared = False

    def set_option(self, key, value):
        self.set_options({key: value})

    def alter_task_search(self, search, prefix='children', prefix_namespace=''):
        # Browser filter criteria belong to the host's search, not hidden CGI state.
        if self.filter_data:
            raise UnsupportedContract('Legacy CGI child task filters are not migrated')
        return search

    def get_tasks(self, sobject=None, pipeline_code=None):
        if not self._prepared:
            self.preprocess()
        return self._get_tasks(sobject=sobject, pipeline_code=pipeline_code)

    def is_sortable(self):
        return False

    @classmethod
    def get_args_keys(cls):
        return cls.ARGS_KEYS

    def _get_tasks(self, sobject=None, pipeline_code=None):
        security = Environment.get_security()
        project_code = Project.get_project_code()

        if not sobject:
            sobject = self.get_current_sobject()

        # If this is the insert table, then there will be no tasks
        if sobject is None or sobject.is_insert():
            return []

        # use parent?
        #sobject = sobject.get_parent()

        search_type = SearchType.build_search_type(sobject.get_search_type(), sobject.get_project_code())

        schema = Schema.get()
        attrs = schema.get_relationship_attrs("sthpw/task", search_type, type=self.relationship_type)
        attrs = schema.resolve_relationship_attrs(attrs, "sthpw/task", search_type)
        to_col = attrs.get("to_col")
        code = sobject.get_value(to_col)
        #search_type = sobject.get_search_type()
        #search_id = sobject.get_id()
        key = "%s|%s" % (search_type, code)

        tasks = self.tasks_dict.get(key)
        if tasks == None:
            tasks = []

        tasks = list(tasks)
        tasks = [task for task in tasks if self.can_view_process(task.get_value('process'))]

        processes = self.kwargs.get("processes")
        if isinstance(processes, basestring):
            processes = processes.split(",")
        elif processes:
            processes = list(processes)

        # get the pipeline
        if not pipeline_code:
            pipeline_code = self.kwargs.get("pipeline_code") or sobject.get_value("pipeline_code", no_exception=True)
            if pipeline_code:
                pipeline_code = pipeline_code.replace("$PROJECT", project_code)

        if pipeline_code:
            pipeline = Pipeline.get_by_code(pipeline_code)
        else:
            pipeline = None

        if pipeline or processes:
            if not processes:
                processes = pipeline.get_process_names()

            supprocess = self.kwargs.get("parent_process")
            if supprocess:
                processes = ["%s.%s" % (supprocess, x) for x in processes]

            processes_remove = []
            for process in processes:
                keys = [
                        { "process": process },
                        { "process": "*" },
                        { "process": process, "project": project_code },
                        { "process": "*", "project": project_code }
                ]
                if not security.check_access("process", keys, "allow", default="deny"):
                    processes_remove.append(process)
            for process in processes_remove:
                processes.remove(process)

            # filter by current pipeline's processes
            # show_current_pipeline_only is not in task_filter since
            # process_only and show_current_pipeline_only are not mutually exclusive
            show_current_pipeline_only = self.kwargs.get('show_current_pipeline_only') != 'false'
            if show_current_pipeline_only:
                filtered_tasks = []
                for task in tasks:
                    process = task.get_value('process')
                    if process in processes:
                        filtered_tasks.append(task)
                tasks = filtered_tasks
            if self.task_filter == 'process_only':
                filtered_tasks = []
                for task in tasks:
                    if task.get_value('process') != task.get_value('context'):
                        continue
                    filtered_tasks.append(task)
                tasks = filtered_tasks
            elif self.task_filter == 'context_only':
                filtered_tasks = []
                for task in tasks:
                    if task.get_value('process') == task.get_value('context'):
                        continue
                    filtered_tasks.append(task)
                tasks = filtered_tasks

            compare = get_compare(processes)
            tasks = sorted(tasks,key=compare)

        else:
            def compare(a,b):
                a_context = a.get_value('process')
                b_context = b.get_value('process')
                return cmp(a_context, b_context)

            tasks = sorted(tasks,key=functools.cmp_to_key(compare))

        self.filler_cache = {}
        # fill in any missing tasks
        pipeline = Pipeline.get_by_code(pipeline_code)
        show_filler_tasks = self.kwargs.get("show_filler_tasks")

        if pipeline and show_filler_tasks in ["true", True]:

            processes = [process for process in pipeline.get_process_names(exclude=["action"])
                         if self.can_view_process("%s.%s" % (self.kwargs["parent_process"], process)
                                                  if self.kwargs.get("parent_process") else process)]
            
            if self.filler_cache == None:
                self.filler_cache = {}

            # get all of the current tasks processes
            existing_processes = [x.get_value("process") for x in tasks]

            supprocess = self.kwargs.get("parent_process")

            for process in processes:

                if supprocess:
                    full_process = "%s.%s" % (supprocess, process)
                else:
                    full_process = process

                # skip processes that already have tasks
                if full_process in existing_processes:
                    continue

                process_pipeline = pipeline
                process_obj = process_pipeline.get_process(process)

                if not process_obj:
                    #print("WARNING: process[%s] not in pipeline [%s]" % (proc
                    continue

                task_pipeline = process_obj.get_task_pipeline()

                task = SearchType.create("sthpw/task")
                task.set_value("process", full_process)
                task.set_value("context", full_process)
                if task_pipeline:
                    task.set_value("pipeline_code", task_pipeline)

                self.filler_cache[full_process] = task

            missing = []
            task_processes = [x.get_value("process") for x in tasks]
            for process in processes:
                if supprocess:
                    full_process = "%s.%s" % (supprocess, process)
                else:
                    full_process = process

                if full_process not in task_processes:
                    missing.append(full_process)

            search_type = sobject.get_search_type()
            search_code = sobject.get_value("code")
            for process in missing:
                task = self.filler_cache.get(process)
                # FIXME: task could be None
                if task:
                    task.set_parent(sobject)
                    tasks.append(task)

            tasks = sorted(tasks,key=get_compare(processes))

        return tasks

    @staticmethod
    def can_view_process(process):
        project = Project.get_project_code()
        return Environment.get_security().check_access('process', [
            {'process': process}, {'process': '*'},
            {'process': process, 'project': project}, {'process': '*', 'project': project}
        ], 'allow', default='deny')

    def get_cell_value(self):
        tasks = self.get_tasks()
        records = []
        parent = self.get_current_sobject()
        code = self.kwargs.get('pipeline_code') or (parent.get_value('pipeline_code', no_exception=True) if parent else '')
        pipeline = self.pipelines_dict.get((code or '').replace('$PROJECT', Project.get_project_code()))
        for task in tasks:
            def value(name):
                return str(task.get_value(name, no_exception=True) or '')
            colors = self.status_colors.get(value('pipeline_code') or 'task', {})
            node = pipeline.get_process(value('process')) if pipeline else None
            record = dict(taskSearchKey='' if task.is_insert() else task.get_search_key(),
                taskCode='' if task.is_insert() else task.get_code(), hasTask=not task.is_insert(),
                processType=node.get_type() if node else 'manual',
                process=value('process'), context=value('context'), status=value('status'),
                statusColor=colors.get(value('status'), ''), assigned=value('assigned'),
                assignedIdentity=self.identities.get(value('assigned')),
                processColor=node.get_color() if node else '', processLabel=node.get_label() if node else value('process'),
                bidStart=value('bid_start_date'), bidEnd=value('bid_end_date'))
            if node and node.get_type() == 'progress':
                if any(item['process'] == record['process'] for item in records):
                    continue
                record['progress'] = self.get_progress_value(parent, pipeline, record['process'])
            records.append(record)
        return dict(text=','.join(':'.join((record['context'], record['status'], record['assigned']))
                                  for record in records), tasks=records,
                    count=sum(record['hasTask'] for record in records))

    @staticmethod
    def get_progress_value(parent, pipeline, process):
        """Legacy TaskElementWdg progress nodes count complete related objects."""
        node = pipeline.get_process(process)
        fields = ('search_type', 'pipeline_code', 'process', 'scope')
        values = {name: node.get_attribute(name) for name in fields}
        if not values['search_type']:
            config = pipeline.get_process_sobject(process)
            workflow = config.get_json_value('workflow', {}) if config else {}
            source = workflow.get('default', {}) if workflow.get('version') in (2, '2') else workflow
            for source in (source, workflow.get('properties') or {}):
                for name in fields:
                    if source.get(name) not in (None, ''):
                        values[name] = source[name]
        result = dict(state='unconfigured', complete=0, total=0, searchKeys=[])
        target = values['search_type']
        if not target:
            return result
        definition = SearchType.get(target, no_exception=True)
        if definition is None:
            result['state'] = 'unavailable'
            return result
        target_project = SearchType.breakup_search_type(target).get('project')
        if target_project and target_project != Project.get_project_code():
            raise SecurityException('Related objects belong to another project')
        if values['scope'] != 'global' and not Schema.get().get_relationship(parent.get_base_search_type(), target):
            result['state'] = 'unavailable'
            return result
        related_process = values['process'] or process
        if not TaskElementWdg.can_view_process(related_process):
            result['state'] = 'unavailable'
            return result
        has_pipeline = SearchType.column_exists(target, 'pipeline_code')
        search = Search(target)
        if has_pipeline and values['pipeline_code']:
            search.add_filter('pipeline_code', values['pipeline_code'])
        # Legacy misspelled its default; an omitted scope must remain local.
        if values['scope'] != 'global':
            search.add_relationship_filter(parent)
        objects = search.get_sobjects()
        keys = {item.get_search_key() + '|' + related_process + '|status': item for item in objects}
        complete = set()
        if keys and has_pipeline:
            messages = Search('sthpw/message')
            messages.add_filters('code', list(keys))
            complete = {item.get_code() for item in messages.get_sobjects()
                        if item.get_value('message') == 'complete'}
        elif objects:
            tasks = Search.get_related_by_sobjects(objects, 'sthpw/task',
                                                    filters=[('process', related_process)])
            completed_parents = {key for key, rows in tasks.items()
                                 if any(str(task.get_value('status') or '').lower() == 'complete'
                                        for task in rows)}
            complete = {key for key, item in keys.items()
                        if str(item.get_value('status', no_exception=True) or '').lower() == 'complete'
                        or item.get_search_key() in completed_parents}
        result.update(state='ready', complete=len(complete), total=len(objects),
                      searchKeys=[item.get_search_key() for item in objects])
        status_message = Search.get_by_code('sthpw/message', parent.get_search_key() + '|' + process + '|status')
        status = str(status_message.get_value('message') or 'pending') if status_message else 'pending'
        result.update(status=status, color=Task.get_default_color(status) or '')
        return result


class TaskSummaryElementWdg(TaskElementWdg):
    ARGS_KEYS = dict(TaskElementWdg.ARGS_KEYS, mode={})

    def __init__(self, **kwargs):
        kwargs.setdefault('show_filler_tasks', True)
        super().__init__(**kwargs)

    def get_cell_value(self):
        cell = super().get_cell_value()
        cell['summaryMode'] = self.get_option('mode') or 'default'
        return cell

    def get_width(self):
        return 100 if self.get_option('mode') == 'minimal' else 400


class TaskElementCbk(DatabaseAction):
    """Original task field callback: NEW/EDIT/COPY/DELETE and initial tasks."""

    def get_title(self):
        return 'Tasks Status Changed'

    def set_sobject(self, sobject):
        self.sobject = sobject

    def postprocess(self):
        if self.xx.get('add_initial_tasks'):
            Task.add_initial_tasks(self.sobject)

    def check_missing(self, tasks, task_id_list):
        missing = set(map(str, task_id_list)) - {str(task.get_id()) for task in tasks}
        if missing:
            raise TacticException('Task with id [%s] no longer exist. Please refresh your view.' % ','.join(sorted(missing)))

    def execute(self):
        from pyasm.web import WebContainer
        web = WebContainer.get_web()
        data = self.data if self.data is not None else self.kwargs.get('data')
        if data is None and web:
            data = (web.get_form_data().get('data') or {}).get('data')
        if isinstance(data, str):
            if len(data.encode()) > 2*1024*1024:
                raise TacticException('Task data is too large')
            try:
                data = json.loads(data)
            except ValueError:
                raise TacticException('Task data is not a valid JSON object. You may need to refresh the view.') from None
        if not isinstance(data, dict) or len(data) > 10000:
            raise TacticException('Task data is not a valid JSON object. You may need to refresh the view.')
        self.xx = data
        self.sobjects = []
        if self.sobject is None:
            self.sobject = Search.get_by_search_key(self.kwargs.get('search_key') or (web.get_form_value('search_key') if web else ''))
        if self.sobject is None:
            raise TacticException('Task parent no longer exists')
        processes = self.kwargs.get('processes')
        if processes is None:
            web_data = web.get_form_value('web_data') if web else {}
            process_data = web_data.get('process_data') if isinstance(web_data, dict) else None
            if isinstance(process_data, str):
                try:
                    process_data = json.loads(process_data)
                except ValueError:
                    process_data = None
            processes = process_data.get('processes') if isinstance(process_data, dict) else []
        if processes is None:
            processes = []
        if not isinstance(processes, list) or any(not isinstance(process, str) for process in processes):
            raise TacticException('Task process order must be a list of names')

        changes = []
        for key, value in data.items():
            match = re.fullmatch(r'(\w+)\|(\w+)\|(.*)', key)
            if not match:
                continue  # Original metadata such as add_initial_tasks is not a field.
            column, action, target = match.groups()
            column = 'bid_duration' if column == 'bid' else column
            if action == 'NEW':
                if not target or len(target) > 256 or any(ord(char) < 32 for char in target):
                    raise TacticException('Choose a valid task process')
                if not TaskElementWdg.can_view_process(target):
                    raise SecurityException('Task process is not accessible')
            elif action in ('EDIT', 'DELETE') or action.startswith('COPY'):
                if action.startswith('COPY'):
                    target = target.split('_', 1)[0]
                if not target.isascii() or not target.isdecimal():
                    raise TacticException('Invalid task identifier')
                target = str(int(target))
                if action == 'EDIT' and column not in ('status', 'assigned', 'bid_duration'):
                    raise TacticException('Column [%s] not supported' % column)
            else:
                continue
            changes.append((column, action, target, value))
        ids = {target for _, action, target, _ in changes if action != 'NEW'}
        existing = {str(task.get_id()): task for task in Task.get_by_sobjects([self.sobject])} if ids else {}
        self.check_missing(list(existing.values()), ids)
        for task_id in ids:
            if not TaskElementWdg.can_view_process(existing[task_id].get_value('process')):
                raise SecurityException('Task process is not accessible')

        new_tasks = {}
        for column, action, target, value in changes:
            if action == 'NEW':
                task = new_tasks.get(target)
                if task is None:
                    task = SearchType.create('sthpw/task')
                    task.set_value('process', target)
                    task.set_parent(self.sobject)
                    new_tasks[target] = task
                task.set_value(column, value)
            elif action.startswith('COPY'):
                source = Search.get_by_id('sthpw/task', target)
                self.check_missing([source] if source is not None else [], [target])
                clone = source.clone()
                clone.set_value('assigned', value)
                clone.commit()
                self.sobjects.append(clone)
            elif action == 'DELETE':
                task = Search.get_by_id('sthpw/task', target)
                self.check_missing([task] if task is not None else [], [target])
                task.delete()

        # Preserve the original reverse workflow order; never lose unlisted NEWs.
        order = list(dict.fromkeys([*reversed(processes), *new_tasks]))
        for process in order:
            if process in new_tasks:
                new_tasks[process].commit()
                self.sobjects.append(new_tasks[process])
        # Original status -> assigned -> bid commits preserve trigger ordering.
        for column in ('status', 'assigned', 'bid_duration'):
            updates = {target: value for field, action, target, value in changes if action == 'EDIT' and field == column}
            if not updates:
                continue
            search = Search('sthpw/task')
            search.add_filters('id', list(updates))
            tasks = search.get_sobjects()
            self.check_missing(tasks, list(updates))
            for task in tasks:
                value = updates[str(task.get_id())]
                if column != 'bid_duration' and task.get_value(column) == value:
                    continue
                task.set_value(column, value)
                task.commit()


class WorkElementWdg(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys(('icon', 'transfer_mode', 'mode'), {})

    def is_editable(self):
        return False

    def get_cell_value(self):
        source = self.get_current_sobject()
        if source is None or source.is_insert():
            return dict(text='', actions=[])
        target = source.get_parent() if source.get_base_search_type() in ('sthpw/task', 'sthpw/note') else source
        if target is None:
            return dict(text='', actions=[], available=False, diagnostic='Parent not found')
        transfer = self.get_option('transfer_mode') or 'upload'
        if transfer not in ('upload', 'copy', 'move'):
            raise ValueError('Invalid configured file transfer mode')
        mode = self.get_option('mode') or 'file'
        if mode != 'file':
            raise ValueError('This configured check-in mode is not available yet')
        return dict(text='', targetSearchKey=target.get_search_key(), taskSearchKey=source.get_search_key(),
                    taskCode=source.get_code() if isinstance(source, Task) else '',
                    process=source.get_value('process', no_exception=True) or 'publish',
                    context=source.get_value('context', no_exception=True) or source.get_value('process', no_exception=True) or 'publish',
                    transferMode=transfer, checkinMode=self.get_option('mode') or 'file',
                    actions=[dict(name='work', label='Work on Task', icon=self.get_option('icon') or 'work')])

