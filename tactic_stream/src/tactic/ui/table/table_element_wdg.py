"""CheckinButtonElementWdg target selection shared with Handler's table."""
# Copyright (c) 2005-2008 Southpaw Technology. All Rights Reserved.
# PROPRIETARY INFORMATION. This software is proprietary to Southpaw Technology.
import re
from pyasm.search import Search
from tactic.ui.common import BaseTableElementWdg
from pyasm.widget.table_element_wdg import PublishTableElement


class GeneralPublishElementWdg(PublishTableElement):
    ARGS_KEYS = dict.fromkeys(('view', 'preview'), {})

    def get_publish_view(self):
        view = self.get_option('view') or 'publish'
        if not isinstance(view, str) or not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', view):
            raise ValueError('Invalid publish view')
        return view

    def preprocess(self):
        self.thumb = None
        if self.get_option('preview') not in ('false', False):
            from pyasm.widget import ThumbWdg
            self.thumb = ThumbWdg(name='preview')
            self.thumb.set_options(self.options)
            self.thumb.set_sobjects(self.sobjects)
            self.thumb.preprocess()

    def get_cell_value(self):
        value = super().get_cell_value()
        if value['available']:
            if not hasattr(self, 'thumb'):
                self.preprocess()
            if self.thumb is not None:
                self.thumb.set_current_index(self.current_index)
                value['preview'] = self.thumb.get_cell_value()
        return value


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


class CheckoutButtonElementWdg(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys(('transfer_mode',), {})

    def is_editable(self):
        return False

    def get_cell_value(self):
        obj = self.get_current_sobject()
        if obj is None or obj.is_insert():
            return dict(text='', actions=[])
        if obj.get_base_search_type() != 'sthpw/snapshot':
            raise ValueError('Check out requires a snapshot')
        unsupported = [name for name, value in self.options.items() if value not in (None, '', False)
            and name not in ('name', 'title', 'class_name', 'transfer_mode')]
        if unsupported:
            raise ValueError('Unsupported checkout options: ' + ', '.join(sorted(unsupported)))
        transfer = self.get_option('transfer_mode') or 'browser'
        if transfer not in ('browser', 'copy', 'client_repo'):
            raise ValueError('Unsupported checkout transfer mode')
        return dict(text='', targetSearchKey=obj.get_search_key(), projectCode=obj.get_value('project_code'),
            requiresDesktop=transfer != 'browser',
            actions=[dict(name='file-checkout', label='Check out', icon='download')])


class NotificationTriggerElementWdg(BaseTableElementWdg):
    def get_cell_value(self):
        return dict(text='', targetSearchKey=self.get_current_sobject().get_search_key(),
                    actions=[dict(name='notification-test', label='Email Test', icon='notifications')])


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
