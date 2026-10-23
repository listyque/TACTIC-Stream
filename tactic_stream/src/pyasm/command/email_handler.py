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

__all__ = [
    "EmailHandler",
    "TaskAssignEmailHandler",
    "NoteEmailHandler",
    "GeneralNoteEmailHandler",
    "GeneralPublishEmailHandler",
    "TaskStatusEmailHandler",
    "TestEmailHandler",
]

import six

from pyasm.common import Environment
from pyasm.security import AccessManager, Login, LoginGroup, Sudo
from pyasm.search import Search, SearchKey, SObject, SearchType
from pyasm.biz import ExpressionParser, GroupNotification, Pipeline, Project, Task


def _resolve_input_sobject(value, default_search_type):
    if not value:
        return None
    if isinstance(value, SObject):
        return value
    if isinstance(value, dict):
        code = value.get("code")
        if code:
            return Search.get_by_code(default_search_type, code)
        skey = value.get("__search_key__") or value.get("search_key")
        if skey:
            return SearchKey.get_by_search_key(skey)
    return None


def _login_can_access_project(login, project_code):
    if not isinstance(login, Login):
        return True
    if login.is_retired():
        return False
    login_name = login.get_login()
    if login_name == "admin":
        return True
    group_names = LoginGroup.get_group_names(login_name)
    if "admin" in group_names:
        return True
    if not project_code or project_code in ("admin", "sthpw"):
        return True
    if not group_names:
        return False
    groups = login.get_sub_groups()
    if not groups:
        return False
    access_manager = AccessManager()
    for group in groups:
        access_manager.add_xml_rules(group)
    keys = [{'code': project_code}, {'code': '*'}]
    user_access = None
    for idx, item in enumerate(keys):
        rule_default = "deny" if idx == len(keys) - 1 else None
        user_access = access_manager.get_access("project", item, default=rule_default)
        if user_access is not None:
            break
    if user_access is None:
        user_access = "deny"
    return access_manager.compare_access(user_access, "allow")


class EmailHandler(object):
    '''Base class for email notifications'''

    def __init__(self, notification, sobject, parent, command, input, login_ticket=None):
        self.notification = notification
        self.sobject = sobject
        self.command = command
        self.parent = parent
        self.input = input or {}

        self.login_ticket = login_ticket

        self.env_sobjects = {
            'sobject': self.sobject
        }

        sudo = Sudo()
        try:
            snapshot = _resolve_input_sobject(self.input.get('snapshot'), "sthpw/snapshot")
            if snapshot:
                self.env_sobjects['snapshot'] = snapshot
            note = _resolve_input_sobject(self.input.get('note'), "sthpw/note")
            if note:
                self.env_sobjects['note'] = note
        finally:
            sudo.exit()

    def check_rule(self):
        '''determine whether an email should be sent'''
        return True

    def send_email(self):
        '''return False to skip sending an email'''
        return True

    def has_ticket(self):
        data = self.notification.get_json_value("data") or {}
        return data.get("login_ticket_create") in ['true', True]

    def set_ticket(self, user=None, expiry=None):
        if isinstance(user, six.string_types):
            login_name = user
        else:
            login_name = user.get_login()
        security = Environment.get_security()
        sudo = Sudo()
        try:
            ticket = security.generate_ticket(login_name, expiry=expiry)
        finally:
            sudo.exit()
        self.login_ticket = ticket

    def get_ticket(self):
        return self.login_ticket

    def _filter_recipients(self, logins):
        recipients = set()
        seen_emails = set()
        project_code = Project.get_project_code()
        sudo = Sudo()
        try:
            for item in logins:
                if not item:
                    continue
                if isinstance(item, Login):
                    if not _login_can_access_project(item, project_code):
                        continue
                    email_key = (item.get_value("email", no_exception=True) or "").strip().lower()
                    if email_key:
                        if email_key in seen_emails:
                            continue
                        seen_emails.add(email_key)
                    recipients.add(item)
                else:
                    email_key = str(item).strip().lower()
                    if "<" in email_key and ">" in email_key:
                        email_key = email_key.split("<", 1)[1].split(">", 1)[0].strip()
                    if email_key:
                        if email_key in seen_emails:
                            continue
                        seen_emails.add(email_key)
                    recipients.add(item)
        finally:
            sudo.exit()
        return recipients

    def get_mail_users(self, column):
        expr = self.notification.get_value(column, no_exception=True)
        logins = []

        if expr:
            sudo = Sudo()
            try:
                env_sobjects = self.env_sobjects.copy()
                parts = []
                for line in expr.split("\n"):
                    line_stripped = line.strip()
                    if not line_stripped or line_stripped.startswith("#"):
                        continue
                    if not (line_stripped.startswith("@") or line_stripped.startswith("{")) and "," in line_stripped:
                        parts.extend(p.strip() for p in line_stripped.split(",") if p.strip())
                    else:
                        parts.append(line_stripped)

                for part in parts:
                    part = part.strip()
                    if not part or part.startswith("#"):
                        continue

                    if part.startswith("@") or part.startswith("{"):
                        results = Search.eval(part, list=True, env_sobjects=env_sobjects)
                        ExpressionParser.clear_cache()
                        if results:
                            if isinstance(results[0], six.string_types):
                                str_results = [r.strip() for r in results if isinstance(r, six.string_types) and r.strip()]
                                if str_results:
                                    login_search = Search("sthpw/login")
                                    login_search.add_filters("login", str_results)
                                    login_sobjs = login_search.get_sobjects()
                                    login_list = set(SObject.get_values(login_sobjs, 'login'))
                                    for result in str_results:
                                        if result not in login_list and "@" in result:
                                            logins.append(result)
                                    if login_sobjs:
                                        logins.extend(login_sobjs)
                            else:
                                logins.extend(results)
                    elif part.find("@") != -1:
                        logins.append(part)
                    elif part:
                        group = LoginGroup.get_by_code(part)
                        if group:
                            logins.extend(group.get_logins())
                        else:
                            login = Login.get_by_login(part)
                            if login:
                                logins.append(login)
            finally:
                sudo.exit()
        elif column == "mail_to":
            notification_id = self.notification.get_id()
            logins = GroupNotification.get_logins_by_id(notification_id)

        return self._filter_recipients(logins)

    def get_to(self):
        return self.get_mail_users("mail_to")

    def get_cc(self):
        return self.get_mail_users("mail_cc")

    def get_bcc(self):
        return self.get_mail_users("mail_bcc")

    def get_subject(self):
        subject = self.notification.get_value("subject", no_exception=True)
        if subject:
            sudo = Sudo()
            try:
                parser = ExpressionParser()
                subject = parser.eval(subject, self.sobject, env_sobjects=self.env_sobjects, mode='string')
            finally:
                sudo.exit()
        else:
            cmd_desc = self.command.get_description() if self.command and hasattr(self.command, "get_description") else ""
            subject = '%s - %s' % (self.sobject.get_update_description(), cmd_desc)
        return subject

    def get_message(self):
        search_type_obj = self.sobject.get_search_type_obj()
        title = search_type_obj.get_title()
        subject = self.get_subject()
        notification_message = self.notification.get_value("message", no_exception=True)
        if notification_message:
            sudo = Sudo()
            try:
                parser = ExpressionParser()

                prev_data = SearchType.create("sthpw/virtual")
                id_col = prev_data.get_id_col()
                if id_col and id_col in prev_data.data:
                    del prev_data.data[id_col]

                prev_dict = self.input.get("prev_data")
                if isinstance(prev_dict, dict):
                    for name, value in prev_dict.items():
                        if value is not None:
                            prev_data.set_value(name, value)

                update_data = SearchType.create("sthpw/virtual")
                id_col = update_data.get_id_col()
                if id_col and id_col in update_data.data:
                    del update_data.data[id_col]

                update_dict = self.input.get("update_data")
                if isinstance(update_dict, dict):
                    for name, value in update_dict.items():
                        if value is not None:
                            update_data.set_value(name, value)

                env_sobjects = self.env_sobjects.copy()
                env_sobjects['prev_data'] = prev_data
                env_sobjects['update_data'] = update_data

                variables = {}
                ticket = self.get_ticket()
                if ticket:
                    env_sobjects['login_ticket'] = ticket
                    variables["TICKET"] = ticket.get_value("ticket", no_exception=True) if isinstance(ticket, SObject) else ticket.get("ticket")

                return parser.eval(
                    notification_message, self.sobject,
                    env_sobjects=env_sobjects, mode='string',
                    vars=variables, keep_newlines=True,
                )
            finally:
                sudo.exit()

        message = "%s %s" % (title, self.sobject.get_name())
        message = '%s\n\nReport from transaction:\n%s\n' % (message, subject)
        return message


class TaskAssignEmailHandler(EmailHandler):
    '''Email sent when a task is assigned'''

    def get_subject(self):
        task = self.sobject
        sobject = task.get_parent()
        name = sobject.get_name() if sobject else task.get_name()

        assigned = task.get_value("assigned")
        task_process = task.get_value("process")
        task_description = task.get_value("description")

        title = "Assignment"
        return "%s: %s to %s (%s) %s" % (title, name, assigned, task_process, task_description)

    def get_to(self):
        recipients = super(TaskAssignEmailHandler, self).get_to()
        task = self.sobject
        assigned = task.get_value("assigned")

        login = Login.get_by_login(assigned)
        if not login:
            Environment.add_warning("Non existent user", "User %s does not exist" % assigned)
            return recipients

        recipients.update(self._filter_recipients([login]))
        return recipients

    def get_message(self):
        task = self.sobject
        assigned = task.get_value("assigned")
        task_process = task.get_value("process")
        task_description = task.get_value("description")
        status = task.get_value("status")

        sobject = task.get_parent()
        if not sobject:
            search_type = task.get_value("search_type")
            search_id = task.get_value("search_id")
            if search_type and search_id:
                sobject = Search.get_by_search_key("%s|%s" % (search_type, search_id))

        msg = [
            "The following task has been assigned to '%s':" % assigned,
            "",
            "Description: %s" % task_description,
            "Process: %s" % task_process,
            "Status: %s" % status,
        ]
        if sobject:
            search_type_obj = sobject.get_search_type_obj()
            title = search_type_obj.get_title()
            code = sobject.get_code()
            name = sobject.get_name()
            msg.append("")
            if name == code:
                msg.append("To %s: %s" % (title, name))
            else:
                msg.append("To %s: %s - (%s)" % (title, name, code))
            if sobject.has_value("description"):
                description = sobject.get_value("description")
                msg.append("\"%s\"" % description)

        return "\n".join(msg)


class NoteEmailHandler(EmailHandler):

    def _get_login(self, assigned):
        return Login.get_by_login(assigned)

    def get_to(self):
        logins = []
        note = self.sobject

        sudo = Sudo()
        try:
            search = Search(Task)
            search.add_filter('search_type', note.get_value('search_type'))
            search.add_filter('search_id', note.get_value('search_id'))
            search.add_filter('process', note.get_process())
            search.add_filter('project_code', note.get_value('project_code'))
            tasks = search.get_sobjects()
            for task in tasks:
                assigned = self._get_login(task.get_assigned())
                if assigned:
                    logins.append(assigned)
                supe = self._get_login(task.get_supervisor())
                if supe:
                    logins.append(supe)
        finally:
            sudo.exit()
        return self._filter_recipients(logins)


class GeneralNoteEmailHandler(EmailHandler):

    def _get_login(self, assigned):
        return Login.get_by_login(assigned)

    def get_to(self):
        logins = []
        note = self.sobject

        sudo = Sudo()
        try:
            search = Search(Task)
            search.add_filter('search_type', note.get_value('search_type'))
            search.add_filter('search_id', note.get_value('search_id'))
            search.add_filter('project_code', note.get_value('project_code'))
            tasks = search.get_sobjects()
            for task in tasks:
                assigned = self._get_login(task.get_assigned())
                if assigned:
                    logins.append(assigned)
                supe = self._get_login(task.get_supervisor())
                if supe:
                    logins.append(supe)
        finally:
            sudo.exit()
        return self._filter_recipients(logins)

    def get_message(self):
        search_type_obj = self.sobject.get_search_type_obj()
        title = search_type_obj.get_title()
        notification_message = self.notification.get_value("message", no_exception=True)

        message = "%s %s" % (title, self.sobject.get_name())
        if notification_message:
            message = "%s (%s)" % (message, notification_message)

        update_desc = self.sobject.get_update_description()
        command_desc = self.command.get_description() if self.command and hasattr(self.command, "get_description") else ""

        return '%s\n\nReport from transaction:\n%s\n\n%s' % (message, update_desc, command_desc)


class GeneralPublishEmailHandler(EmailHandler):
    '''On publish of a shot/asset, find all assignees and supervisors of its tasks.'''

    def _get_login(self, assigned):
        return Login.get_by_login(assigned)

    def get_to(self):
        recipients = super(GeneralPublishEmailHandler, self).get_to()
        sobj = self.sobject
        logins = []

        sudo = Sudo()
        try:
            search = Search(Task)
            search.add_filter('search_type', sobj.get_search_type())
            search.add_filter('search_id', sobj.get_id())
            search.add_filter('project_code', Project.get_project_code())
            tasks = search.get_sobjects()
            for task in tasks:
                assigned = self._get_login(task.get_assigned())
                if assigned:
                    logins.append(assigned)
                supe = self._get_login(task.get_supervisor())
                if supe:
                    logins.append(supe)
        finally:
            sudo.exit()
        recipients.update(self._filter_recipients(logins))
        return recipients

    def get_message(self):
        search_type_obj = self.sobject.get_search_type_obj()
        title = search_type_obj.get_title()
        notification_message = self.notification.get_value("message", no_exception=True)

        message = "%s %s" % (title, self.sobject.get_name())
        if notification_message:
            message = "%s (%s)" % (message, notification_message)

        update_desc = self.sobject.get_update_description()
        command_desc = self.command.get_description() if self.command and hasattr(self.command, "get_description") else ""

        return '%s\n\nReport from transaction:\n%s\n\n%s' % (message, update_desc, command_desc)


class TaskStatusEmailHandler(EmailHandler):

    def _get_login(self, assigned):
        return Login.get_by_login(assigned)

    def get_to(self):
        recipients = super(TaskStatusEmailHandler, self).get_to()
        sobj = self.sobject
        logins = []

        sudo = Sudo()
        try:
            if not isinstance(sobj, Task):
                tasks = Task.get_by_sobject(sobj)
            else:
                tasks = [sobj]

            for task in tasks:
                assigned = self._get_login(task.get_assigned())
                if assigned:
                    logins.append(assigned)
                supe = self._get_login(task.get_supervisor())
                if supe:
                    logins.append(supe)
        finally:
            sudo.exit()
        recipients.update(self._filter_recipients(logins))
        return recipients


class TestEmailHandler(EmailHandler):

    def check_rule(self):
        task = self.sobject
        self.parent = task.get_parent()
        if not self.parent:
            return False
        pipeline_code = self.parent.get_value("pipeline_code", no_exception=True)
        self.pipeline = Pipeline.get_by_code(pipeline_code) if pipeline_code else None
        if not self.pipeline:
            return False
        return task.get_value("status") == "Review"
