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

"""Original native trigger callbacks; HTML editors are excluded."""
import ast
import os
import xml.etree.ElementTree as ET
from pyasm.common import jsondumps
from pyasm.biz import Notification, Project
from pyasm.command import Command
from pyasm.search import Search, SearchType, SearchKey
from pyasm.security.security import _require_admin


class BaseTriggerEditCbk(Command):

    def get_trigger(self):
        _require_admin()
        # Create the trigger from the options


        scope = self.kwargs.get("scope")


        search_key = self.kwargs.get("search_key")

        event = self.kwargs.get("event")
        if event == '__custom__':
            event = self.kwargs.get("custom_event")


        pipeline_code = self.kwargs.get("pipeline_code")
        process = self.kwargs.get("process")
        listen_process = self.kwargs.get("listen_process")
        search_type = self.kwargs.get("search_type")

        code = self.kwargs.get("code")
        title = self.kwargs.get("title")
        description = self.kwargs.get("description") 



        if search_key:
            trigger = Search.get_by_search_key(search_key)
            if not trigger or trigger.get_base_search_type() not in ('config/trigger', 'sthpw/notification'):
                raise ValueError('Select a trigger or notification')
            if trigger.get_base_search_type() != 'config/trigger':
                trigger.delete()
                trigger = SearchType.create("config/trigger")
        else:
            trigger = SearchType.create("config/trigger")


        if code:
            trigger.set_value("code", code)

        trigger.set_value("event", event)
        trigger.set_value("title", title)
        trigger.set_value("description", description)


        if process:
            if scope == "local":
                pipeline_code = self.kwargs.get("pipeline_code")
                search = Search("config/process")
                search.add_filter("pipeline_code", pipeline_code)
                search.add_filter("process", process)
                process_sobj = search.get_sobject()
                if not process_sobj:
                    raise ValueError('Select a process from this pipeline')
                trigger.set_value("process", process_sobj.get_code())
            else:
                trigger.set_value("process", process)


        if listen_process:
            trigger.set_value("listen_process", listen_process)

        if search_type:
            trigger.set_value("search_type", search_type)
        else: 
            if event.startswith('checkin'):
                trigger.set_value("search_type", "")



        class_name = self.get_class_name()
        if class_name:
            trigger.set_value("class_name", class_name)
            trigger.set_value("script_path", "")
        else:
            trigger.set_value("class_name", "")
            trigger.set_value("script_path", "")



        trigger.set_value("mode", 'same process,same transaction')

        return trigger

class StatusTriggerEditCbk(BaseTriggerEditCbk):


    def get_class_name(self): 
        class_name = 'tactic.command.PipelineTaskStatusTrigger'
        return class_name


    def execute(self):


        self.process = self.kwargs.get("process")
        self.src_status = self.kwargs.get("src_status")
        
        dst_statuses = self.kwargs.get("dst_status")
        dst_processes = self.kwargs.get("dst_process")
        self.dst_statuses = []
        self.dst_processes = []
        for tmp_status, tmp_process in zip(dst_statuses, dst_processes):
            if tmp_process:
                self.dst_statuses.append(tmp_status)
                self.dst_processes.append(tmp_process)
                

        # Build a data structure for this.  Use a very simple one-to-one
        # rule/action setup
        data_list = []
        for i, dst_process in enumerate(self.dst_processes):
            dst_status = self.dst_statuses[i]
            data = {
                "src_process": self.process,
                "src_status": self.src_status,
                "dst_process": dst_process,
                "dst_status": dst_status
            }
            data_list.append(data)

        data = jsondumps(data_list)


        trigger = self.get_trigger()


        trigger.set_value("data", str(data))
        trigger.commit()


        search_key = SearchKey.get_by_sobject(trigger)
        self.info['search_key'] = search_key

class TriggerParentStatusEditCbk(BaseTriggerEditCbk):

    def get_class_name(self): 
        class_name = 'tactic.command.PipelineParentStatusTrigger'
        return class_name


    def execute(self):

        self.process = self.kwargs.get("process")
        dst_status = self.kwargs.get("dst_status")

        data = {
            'dst_status': dst_status
        }


        trigger = self.get_trigger()

        trigger.set_value("data", jsondumps(data))
        trigger.commit()


        search_key = SearchKey.get_by_sobject(trigger)
        self.info['search_key'] = search_key

class TriggerDateCbk(BaseTriggerEditCbk):

    def get_class_name(self): 
        class_name = 'tactic.command.PipelineTaskDateTrigger'
        return class_name



    def execute(self):

        src_status = self.kwargs.get("src_status")
        column = self.kwargs.get("column")

        trigger = self.get_trigger()

        data = {
            'src_status': src_status,
            'column': column
        }
        trigger.set_value("data", jsondumps(data))

        trigger.commit()

        search_key = SearchKey.get_by_sobject(trigger)
        self.info['search_key'] = search_key

class TriggerCreateCbk(BaseTriggerEditCbk):

    def get_class_name(self): 
        class_name = 'tactic.command.PipelineTaskCreateTrigger'
        return class_name



    def execute(self):

        outputs = self.kwargs.get("output")
        if isinstance(outputs, str) and outputs:
            outputs = [outputs]
        elif isinstance(outputs, list):
            outputs = [p for p in outputs if p]
        else:
            outputs = []
            
        data = {
            'output': outputs
        }
        
        src_status =  self.kwargs.get("src_status")
        if src_status:
            data["src_status"] = src_status
        
        trigger = self.get_trigger()
        trigger.set_value("data", jsondumps(data))
        trigger.commit()

        search_key = SearchKey.get_by_sobject(trigger)
        self.info['search_key'] = search_key

class NotificationGetTemplateCbk(Command):

    def execute(self):

        event = self.kwargs.get("event")
        search_type = self.kwargs.get("search_type")

        if event.startswith("insert|")and not event.startswith("insert|sthpw/"):
            event = "insert"
        elif event.startswith("update|")and not event.startswith("update|sthpw/"):
            event = "update"
        elif event.startswith("change|")and not event.startswith("change|sthpw/"):
            event = "change"


        path = __file__
        dirname = os.path.dirname(path)
        path = "%s/mail_templates.py" % (dirname)

        f = open(path, 'r')
        contents = f.read()
        f.close()

        templates = ast.literal_eval(contents)

        mail = templates.get(event)
        if not mail:
            mail = {
                'subject': '',
                'message': ''
            }

        self.info = mail

class NotificationTriggerEditCbk(Command):

    def execute(self):
        _require_admin()
        notification = None

        search_key = self.kwargs.get("search_key")
        if search_key:
            notification = Search.get_by_search_key(search_key) 
            # verify if this is a trigger search_key or notification search_key
            # it could be a trigger search_key when editing an existing trigger
            if not isinstance(notification, Notification):
                notification = None
        process = self.kwargs.get("process")
        scope = self.kwargs.get("scope")
        listen_process = self.kwargs.get("listen_process")
        search_type = self.kwargs.get("search_type")
        use_default = self.kwargs.get("default") == 'on'

        login_ticket_create = self.kwargs.get("login_ticket_create") == "on"

        title = self.kwargs.get("title")
        description = self.kwargs.get('description')

        event = self.kwargs.get("event")

        if event == '__custom__':
            event = self.kwargs.get("custom_event")
        assert event
        subject = self.kwargs.get("subject")
        message = self.kwargs.get("body")
        mail_to = self.kwargs.get("mail_to")
        mail_cc = self.kwargs.get("mail_cc")

        project_code = Project.get_project_code()

        if not notification:
            notification = SearchType.create("sthpw/notification")

        notification.set_value("event", event)
        notification.set_value("title", title)

        # listen process takes precesdencce
        if listen_process:
            notification.set_value("process", listen_process)
        elif process:
            if scope == "local":
                pipeline_code = self.kwargs.get("pipeline_code")
                search = Search("config/process")
                search.add_filter("pipeline_code", pipeline_code)
                search.add_filter("process", process)
                process_sobj = search.get_sobject()
                if not process_sobj:
                    raise ValueError('Select a process from this pipeline')
                notification.set_value("process", process_sobj.get_code())
            else:
                notification.set_value("process", process)
        if search_type:
            notification.set_value("search_type", search_type)

        if use_default:
            cmd = NotificationGetTemplateCbk(event=event)
            cmd.execute()
            info = cmd.get_info()
            subject = info.get("subject")
            message = info.get("message")


        notification.set_value("subject", subject)
        notification.set_value("description", description)
        notification.set_value("message", message)
        notification.set_value("mail_to", mail_to)
        notification.set_value("mail_cc", mail_cc)
        notification.set_value("project_code", project_code)


        data = notification.get_json_value("data") or {}

        # unfortunately, notifications have a different filter method than
        # normal triggers ... this needs to made all consistent at some point
        src_status = self.kwargs.get("src_status")
        if src_status:
            root = ET.Element('rules')
            ET.SubElement(root, 'rule').text = '@GET(.status) == ' + repr(src_status)
            rules = ET.tostring(root, encoding='unicode')
            notification.set_value("rules", rules)

            # Build a data structure for this.  Use a very simple one-to-one
            # rule/action setup
            data["src_process"] = process
            data["src_status"] = src_status



        data["login_ticket_create"] = login_ticket_create;
        notification.set_json_value("data", data)


        notification.commit()

        search_key = SearchKey.get_by_sobject(notification)
        self.info['search_key'] = search_key

class PythonScriptTriggerEditCbk(BaseTriggerEditCbk):

    def get_class_name(self): 
        return None



    def execute(self):

        scope = self.kwargs.get("scope")
        language = self.kwargs.get("language")

        trigger = self.get_trigger()

        # Get the trigger code
        trigger_code = self.kwargs.get('code')
        if not trigger_code:
            trigger_code = trigger.get_value("code")
            if not trigger_code:
                # if a code does not exist yet
                trigger.commit()
                trigger_code = trigger.get_value("code")

        script_path = self.kwargs.get("script_path")

        # Update the trigger
        trigger.set_value("code", trigger_code)

        event = self.kwargs.get("event")
        if event == "change|sthpw/task|status":
            src_status = self.kwargs.get("src_status")
            src_process = self.kwargs.get("process")
            data = {
                'src_status': src_status,
                'src_process': src_process
            }
            data = jsondumps(data)
            # trigger.set_value("script_path", script_path)
            trigger.set_value("data", data)
            trigger.set_value("class_name", "tactic.command.PipelineTaskStatusTrigger")
        else:
            trigger.set_value("class_name", "")
            trigger.set_value("data", "")

        trigger.set_value("script_path", script_path)

        trigger.commit()
        
        search_key = SearchKey.get_by_sobject(trigger)
        self.info['search_key'] = search_key

class PythonClassTriggerEditCbk(BaseTriggerEditCbk):

    def get_class_name(self):
        return None

    def execute(self):

        trigger = self.get_trigger()

        class_path = self.kwargs.get("class_path")  
        event = self.kwargs.get("event")
        
        if event == "change|sthpw/task|status":
            data = {'class_path': class_path}
            src_status = self.kwargs.get("src_status")
            src_process = self.kwargs.get("process")
            if src_status:
                data['src_status'] = src_status
            if src_process:
                data['src_process'] = src_process
            data = jsondumps(data)
            trigger.set_value("data", data)
            trigger.set_value("class_name", "tactic.command.PipelineTaskStatusTrigger")
        else:
            trigger.set_value("class_name", class_path)
            trigger.set_value("data", "")
 
        trigger.commit()
        
        search_key = SearchKey.get_by_sobject(trigger)
        self.info['search_key'] = search_key
