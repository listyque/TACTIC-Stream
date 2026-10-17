"""CheckinButtonElementWdg target selection shared with Handler's table."""
# Copyright (c) 2005-2008 Southpaw Technology. All Rights Reserved.
# PROPRIETARY INFORMATION. This software is proprietary to Southpaw Technology.
import re
from pyasm.search import Search
from tactic.ui.common import BaseTableElementWdg


class CheckinButtonElementWdg(BaseTableElementWdg):
    def is_editable(self):
        return False

    def get_cell_value(self):
        target = source = self.get_current_sobject()
        process = self.get_option('process') or 'publish'
        context = process
        if source.get_base_search_type() in ('sthpw/task', 'sthpw/note'):
            process = source.get_value('process', no_exception=True) or ''
            context = source.get_value('context', no_exception=True) or ''
            if re.search(r'/(\d+)$', context):
                context = ''
            mode = self.get_option('sobject_mode') or 'parent'
            if mode == 'parent':
                target = source.get_parent()
            elif mode in ('connect', 'expression'):
                target = Search.eval('@SOBJECT(connect)', source, single=True)
            if not target:
                return dict(text='', available=False)
        return dict(text='', available=True, targetSearchKey=target.get_search_key(use_id=False),
                    process=process, context=context or process, checkinMode=self.get_option('mode') or '',
                    transferMode=self.get_option('transfer_mode') or '')


class RecipientElementWdg(BaseTableElementWdg):
    def preprocess(self):
        search = Search('sthpw/notification_login')
        search.add_filters('notification_log_id', [obj.get_id() for obj in self.sobjects])
        self.recipients = {}
        for row in search.get_sobjects() if self.sobjects else []:
            self.recipients.setdefault(row.get_value('notification_log_id'), []).append(row)

    def get_logins(self):
        return self.recipients.get(self.get_current_sobject().get_id(), [])

    def get_cell_value(self):
        rows = [{'title': row.get_value('type'), 'value': row.get_value('login')} for row in self.get_logins()]
        return {'text': '\n'.join('%s: %s' % (row['title'], row['value']) for row in rows), 'entries': rows}
