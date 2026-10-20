# Copyright (c) 2010 Southpaw Technology. See LICENSE.TACTIC.
"""Original notification test command; trigger execution remains the owner."""

from pyasm.common import Environment, TacticException
from pyasm.command import Command, Trigger
from pyasm.search import SearchKey, SearchType
from pyasm.biz import Project
from pyasm.security.security import _require_admin


class NotificationTestCmd(Command):
    def get_base_search_type(self):
        return ''

    def get_prev_value(self):
        return ''

    def execute(self):
        _require_admin()
        notification = self.kwargs.get('sobject_dict')
        if not isinstance(notification, dict):
            raise ValueError('A notification definition is required')
        event = notification.get('event') or ''
        parts = event.split('|')
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise TacticException('event should be in the form of {action}|{search_type}, e.g. update|sthpw/task or update|sthpw/task|status')
        original_type = parts[1]
        search_type_obj = SearchType.get(original_type)
        sobject = SearchType.create(original_type)
        self.sobjects.append(sobject)
        search_type = SearchKey.extract_search_type(notification.get('__search_key__') or '')
        columns = search_type_obj.get_columns(original_type)
        for column in columns:
            data_type = search_type_obj.get_column_type(original_type, column)
            if column == 'search_type':
                value = search_type
            elif column == 'search_id':
                value = notification.get('id')
            elif column == 'project_code':
                value = Project.get_project_code()
            elif column in ('assigned', 'login'):
                value = Environment.get_user_name()
            elif data_type in ('integer', 'float', 'number'):
                value = 100
            elif data_type == 'timestamp':
                value = '20110101'
            else:
                value = column + '_test'
            sobject.set_value(column, value)
        if notification.get('search_type'):
            sobject.set_value('search_type', notification['search_type'])
        process = notification.get('process')
        if process and 'process' in columns:
            sobject.set_value('process', process)
        triggers = Trigger.call(sobject, event, output={'id': sobject.get_id()},
                                forced_mode='same process,same transaction',
                                process=process, search_type=notification.get('search_type'))
        if not triggers:
            raise TacticException('No notification trigger is fired. Possible mismatched project_code for this notification entry.')
        for index, trigger in enumerate(triggers):
            self.add_description('%s. %s' % (index + 1, trigger.get_description()))
