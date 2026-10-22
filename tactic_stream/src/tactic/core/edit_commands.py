# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Original form commands; HTML rendering is excluded."""
__all__ = ['EditCmdException', 'EditCmd', 'EditMultipleCmd']
from pyasm.common import Common, Environment, TacticException, jsonloads
from pyasm.search import Search, SearchType, SearchKey, SqlException
from pyasm.command import Command
from pyasm.security import Sudo

basestring = str
import six

class EditCmdException(Exception):
    pass


class EditCmd(Command):

    def __init__(self, **kwargs):
        from pyasm.web import WebContainer
        from pyasm.web import Web
        if WebContainer.get_web() is None:
            WebContainer.set_web(Web())
        web = WebContainer.get_web()
        self.view = kwargs.get('view')
        if not self.view:
            self.view = 'edit'
        self.search_key = kwargs.get('search_key')
        self.trigger_mode = kwargs.get('trigger_mode')
        if self.trigger_mode == None:
            self.trigger_mode = True
        self.data = kwargs.get('data')
        if self.data != None:
            self.element_names = list(self.data.keys())
        else:
            self.element_names = kwargs.get('element_names')
        form_data = web.get_form_value('__data__')
        if form_data:
            if isinstance(form_data, list):
                form_data = form_data[0]
            if isinstance(form_data, six.string_types):
                form_data = jsonloads(form_data)
            assert isinstance(form_data, dict)
            self.config_xml = form_data.get('config_xml')
            if not self.config_xml:
                self.config_xml = kwargs.get('config_xml') or None
        else:
            form_data = {}
            self.config_xml = kwargs.get('config_xml')
        self.multiplier = 1
        self.multiplier_str = kwargs.get('multiplier')
        if not self.multiplier_str:
            self.multiplier_str = web.get_form_value('multiplier')
        if self.multiplier_str:
            try:
                self.multiplier = int(self.multiplier_str)
            except:
                pass
        self.parent_key = kwargs.get('parent_key')
        self.connect_key = kwargs.get('connect_key')
        self.input_prefix = kwargs.get('input_prefix')
        if not self.input_prefix:
            self.input_prefix = 'edit'
        elif self.input_prefix == '__NONE__':
            self.input_prefix = ''
        self.extra_data = kwargs.get('extra_data') or {}
        if isinstance(self.extra_data, basestring):
            self.extra_data = jsonloads(self.extra_data)
        self.extra_action = kwargs.get('extra_action') or {}
        self.expected_revision = kwargs.get('expected_revision')
        self.action = kwargs.get('action') or 'save'
        super(EditCmd, self).__init__()
        self.search_type = None
        self.sobject = kwargs.get('sobject')
        self.update = True
        if self.multiplier < 1:
            raise EditCmdException('Multiplier must be positive')

    def get_sobject(self):
        return self.sobject

    def is_api_executable(self):
        return True

    def get_title(self):
        return 'Insert/Edit Item'

    def get_default_action_handler(self):
        return 'DatabaseAction'

    def check(self):
        """this should return True by default now since it is not run
           by default"""
        return True

    def execute(self):
        last_sobject = None
        last_code = None
        last_name = None
        for index in range(0, self.multiplier):
            if last_code:
                code = Common.get_next_code(last_code)
            else:
                code = None
            if last_name:
                name = Common.get_next_code(last_name)
            else:
                name = None
            last_sobject = self._execute_single(code, name=name)
            last_code = last_sobject.get_value('code', no_exception=True)
            if SearchType.column_exists(last_sobject.get_search_type(), 'name'):
                last_name = last_sobject.get_value('name', no_exception=True)
                if index == 0 and self.multiplier > 1:
                    name = Common.get_next_code(last_name)
                    last_sobject.set_value('name', name)
                    last_sobject.commit()
                    last_name = last_sobject.get_value('name', no_exception=True)

    def _get_action_handlers(self):
        search_type_obj = SearchType.get(self.search_type)
        default_elements = []
        from tactic.core.widget_config import WidgetConfigView, WidgetConfig
        tmp_config = WidgetConfigView.get_by_search_type(self.search_type, self.view, layout='EditCmd')
        tmp_element_names = tmp_config.get_element_names()
        for element_name in tmp_element_names:
            action_handler = tmp_config.get_action_handler(element_name)
            if action_handler == 'DefaultValueDatabaseAction':
                default_elements.append(element_name)
        if not self.element_names:
            config = WidgetConfigView.get_by_search_type(search_type_obj, self.view)
            self.element_names = config.get_element_names()
        elif self.config_xml:
            config = WidgetConfigView.get_by_search_type(search_type_obj, self.view)
            extra_config = WidgetConfig.get(view='tab', xml=self.config_xml)
            config.get_configs().insert(0, extra_config)
            extra_config = WidgetConfig.get(view='edit', xml=self.config_xml)
            config.get_configs().insert(0, extra_config)
        else:
            base_view = self.view
            config = WidgetConfigView.get_by_element_names(self.search_type, self.element_names, base_view=base_view)
        display_view = 'table'
        display_config = WidgetConfigView.get_by_search_type(search_type_obj, display_view)
        for element_name in default_elements:
            if element_name not in self.element_names:
                self.element_names.append(element_name)
        assert self.element_names
        assert config
        action_handlers = []
        for element_name in self.element_names:
            action_handler_class = config.get_action_handler(element_name)
            display_item = next((item for item in (*config.get_configs(), *display_config.get_configs()) if item.get_display_handler(element_name)), None)
            display_class = display_item.get_display_handler(element_name) if display_item else ''
            display_options = display_item.get_display_options(element_name) if display_item else {}
            upload_display = display_class in (
                'SimpleUploadWdg', 'tactic.ui.widget.SimpleUploadWdg', 'tactic.ui.widget.upload_wdg.SimpleUploadWdg',
                'UploadWdg', 'pyasm.widget.UploadWdg', 'pyasm.widget.input_wdg.UploadWdg',
                'tactic.ui.widget.UploadWdg', 'tactic.ui.widget.upload_wdg.UploadWdg',
            )
            if not action_handler_class and not SearchType.column_exists(self.search_type, element_name) and not upload_display:
                if element_name not in ['workflow']:
                    continue
            if action_handler_class in ('NullAction', 'pyasm.command.NullAction') and display_class in ('UploadWdg', 'pyasm.widget.UploadWdg', 'pyasm.widget.input_wdg.UploadWdg', 'tactic.ui.widget.UploadWdg', 'tactic.ui.widget.upload_wdg.UploadWdg'):
                action_handler_class = ''
            if not action_handler_class:
                try:
                    action_handler_class = Common.resolve_class(display_class).get_default_action()
                except Exception:
                    action_handler_class = ''
                if display_class in ('tactic.ui.widget.UploadWdg', 'tactic.ui.widget.upload_wdg.UploadWdg') and display_options.get('names'):
                    action_handler_class = 'MultiUploadAction'
            if action_handler_class == '':
                action_handler_class = self.get_default_action_handler()
            action_handler = WidgetConfig.create_widget(action_handler_class)
            action_handler.set_name(element_name)
            action_handler.set_input_prefix(self.input_prefix)
            action_options = dict(config.get_action_options(element_name))
            if action_handler_class in ('MultiUploadAction', 'pyasm.command.MultiUploadAction', 'pyasm.command.edit_wdg_action.MultiUploadAction') and display_options.get('names'):
                action_options.setdefault('names', display_options['names'])
                action_options.setdefault('types', '|'.join('icon_main' if 'icon' in item else 'main' for item in str(action_options['names']).split('|')))
            elif action_handler_class in ('UploadAction', 'pyasm.command.UploadAction', 'pyasm.command.edit_wdg_action.UploadAction'):
                for key in ('context', 'type', 'column'):
                    if display_options.get(key):
                        action_options.setdefault(key, display_options[key])
            if self.data != None:
                element_data = self.data.get(element_name)
                action_handler.set_data(element_data)
            for key, value in action_options.items():
                action_handler.set_option(key, value)
            action_handlers.append(action_handler)
        for action_handler_class, data in self.extra_action.items():
            element_name = action_handler_class
            action_handler = Common.create_from_class_path(action_handler_class)
            action_handler.set_name(element_name)
            action_handler.set_input_prefix(self.input_prefix)
            if self.data != None:
                element_data = self.data.get(element_name)
                action_handler.set_data(element_data)
            for key, value in data.items():
                action_handler.set_option(key, value)
            action_handlers.append(action_handler)
        return action_handlers

    def _execute_single(self, code, name=None):
        from pyasm.web import WebContainer
        web = WebContainer.get_web()
        no_commit = web.get_form_value('sobject_commit') == 'false'
        sobject = None
        if self.search_key:
            sudo = Sudo()
            try:
                sobject = SearchKey.get_by_search_key(self.search_key)
                if sobject and (self.expected_revision or self.action == 'check') and self.action != 'check':
                    sql = sobject.get_sql()
                    sql.get_database_impl().lock_collection_table(sql, sobject.get_table())
                    sobject = SearchKey.get_by_search_key(self.search_key)
            finally:
                sudo.exit()
            if not sobject:
                raise TacticException('This search key [%s] no longer exists.' % self.search_key)
            if sobject.is_retired():
                raise TacticException('Retired records cannot be edited. Reactivate the record first.')
            if self.expected_revision or self.action == 'check':
                import hashlib
                import json
                current_rev = hashlib.sha256(json.dumps(sobject.get_data(), sort_keys=True, default=str).encode()).hexdigest()
                if self.action == 'check':
                    self.search_type = sobject.get_search_type()
                    probe = SearchType.create(self.search_type)
                    for k, v in sobject.get_data().items():
                        if v is not None:
                            probe.set_value(k, v)
                    for action_handler in self._get_action_handlers():
                        if action_handler.__class__.__name__ in ('UploadAction', 'MultiUploadAction', 'MultiZipUploadAction'):
                            continue
                        action_handler.set_sobject(probe)
                        if action_handler.check():
                            action_handler.execute()
                    matches = bool(probe.update_data) and all(
                        str(sobject.get_value(col, no_exception=True) or '') == str(val or '')
                        for col, val in probe.update_data.items()
                    )
                    self.sobject = sobject
                    self.info['state'] = 'saved' if matches else ('unchanged' if current_rev == self.expected_revision else 'conflict')
                    self.info['search_key'] = SearchKey.get_by_sobject(sobject, use_id=True)
                    self.info['sobject'] = sobject.get_sobject_dict()
                    return sobject
                if self.expected_revision and current_rev != self.expected_revision:
                    raise TacticException('Record changed. Reload before saving.')
            self.search_type = sobject.get_search_type()
        elif self.sobject:
            sobject = self.sobject
            self.search_type = sobject.get_search_type()
        else:
            self.search_type = web.get_form_value('search_type')
            if self.search_type == '':
                raise EditCmdException('Search type not found')
            search_id = web.get_form_value('search_id')
            if search_id == '' or search_id == '-1':
                sobject = SearchType.create(self.search_type)
            else:
                sudo = Sudo()
                try:
                    search = Search(self.search_type)
                    search.add_id_filter(search_id)
                    sobject = search.get_sobject()
                finally:
                    sudo.exit()
                if sobject == None:
                    raise EditCmdException('No sobject found with search type [%s] and id [%s]' % (self.search_type, search_id))
        action_handlers = self._get_action_handlers()
        for action_handler in action_handlers:
            action_handler.set_sobject(sobject)
            if action_handler.check():
                if self.parent_key:
                    action_handler.set_option('parent_key', self.parent_key)
                if self.connect_key:
                    action_handler.set_option('connect_key', self.connect_key)
                action_handler.execute()
        if sobject.is_insert() and self.parent_key:
            sobject.add_relationship(self.parent_key)
        if code:
            sobject.set_value('code', code)
        if name:
            sobject.set_value('name', name)
        for key, value in self.extra_data.items():
            if key == 'data':
                continue
            sobject.set_value(key, value)
        if sobject.is_insert():
            action = 'Inserted'
        else:
            action = 'Updated'
        update_data = sobject.update_data
        for key, value in update_data.items():
            if value and SearchType.column_exists(self.search_type, key):
                self.info[key] = value
        if not no_commit:
            try:
                if sobject.is_insert():
                    is_insert = True
                else:
                    is_insert = False
                sobject.commit(triggers=self.trigger_mode)
                if is_insert and self.connect_key and (self.connect_key != '__NONE__'):
                    sobject.connect(self.connect_key, 'task')
            except SqlException as e:
                msg = 'An error was encountered adding this item.  The error reported was [%s]' % e
                raise SqlException(msg)
            self.add_description(sobject.get_update_description())
        for action_handler in action_handlers:
            try:
                action_handler.post_execute()
            except Exception as e:
                print('WARNING: ', e)
        self.sobject = sobject
        for action_handler in action_handlers:
            action_handler.postprocess()
            action_desc = action_handler.get_description()
            if action_desc:
                self.add_description(action_desc)
        self.sobjects.append(sobject)
        self.info['action'] = action
        self.info['search_key'] = SearchKey.get_by_sobject(sobject, use_id=True)
        self.info['sobject'] = sobject.get_sobject_dict()
        return sobject


class EditMultipleCmd(Command):
    """Do multiple edits in a single call"""

    def __init__(self, **kwargs):
        super(EditMultipleCmd, self).__init__(**kwargs)
        self.update = True

    def execute(self):
        """
        var kwargs = {
            search_keys: search_keys,
            view: 'edit_item',
            element_names: element_names,
            input_prefix: '__NONE__',
            update_data: update_data
        }
        """
        parent_key = self.kwargs.get('parent_key')
        connect_key = self.kwargs.get('connect_key')
        search_keys = self.kwargs.get('search_keys')
        view = self.kwargs.get('view')
        element_names = self.kwargs.get('element_names')
        input_prefix = self.kwargs.get('input_prefix')
        update_data = self.kwargs.get('update_data')
        update_data = jsonloads(update_data)
        config_xml = self.kwargs.get('config_xml')
        trigger_mode = self.kwargs.get('trigger_mode')
        extra_data = self.kwargs.get('extra_data')
        extra_data = jsonloads(extra_data)
        extra_action = self.kwargs.get('extra_action')
        extra_action = jsonloads(extra_action)
        plans = self.kwargs.get('plans') or []
        if isinstance(plans, basestring):
            plans = jsonloads(plans)
        plan_map = {item.get('search_key'): item.get('expected_revision') for item in plans if isinstance(item, dict)}
        action = self.kwargs.get('action') or 'save'
        states = []
        edit_search_keys = []
        from pyasm.web import WebContainer
        web = WebContainer.get_web()
        web_data = web.get_form_value('web_data')
        web_data_list = None
        if web_data:
            web_data_list = jsonloads(web_data)
        sk_dict = {}
        search_types = set()
        for i, search_key in enumerate(search_keys):
            data = update_data[i]
            extra = extra_data[i]
            if extra:
                for name, value in extra.items():
                    if not name in data:
                        data[name] = value
            if web_data_list:
                single_web_data = web_data_list[i]
                web.set_form_value('web_data', single_web_data)
            command_class = getattr(self, 'edit_command_class', EditCmd)
            cmd = command_class(parent_key=parent_key, connect_key=connect_key, search_key=search_key, view=view, data=data, input_prefix=input_prefix, extra_action=extra_action[i], trigger_mode=trigger_mode, config_xml=config_xml, expected_revision=plan_map.get(search_key), action=action)
            cmd.execute()
            if action == 'check':
                states.append(cmd.info.get('state', 'conflict'))
                continue
            sobject = cmd.get_sobject()
            search_key = sobject.get_search_key(use_id=True)
            edit_search_keys.append(search_key)
            base_search_type = sobject.get_base_search_type()
            search_types.add(base_search_type)
            sk_data_list = sk_dict.get(base_search_type)
            if not sk_data_list:
                sk_data_list = []
                sk_dict[base_search_type] = sk_data_list
            sk_data_list.append((search_key, data))
        if action == 'check':
            self.info['state'] = states[0] if len(set(states)) == 1 else 'conflict'
            return
        self.info['search_keys'] = edit_search_keys
        search_types = list(search_types)
        search_types_label = ', '.join(search_types)
        self.add_description('Updated [%s] item/s in types [%s]' % (len(search_keys), search_types_label))
        from pyasm.command import Trigger
        prefix = 'update_multi'
        for search_type in search_types:
            sk_data_list = sk_dict.get(search_type)
            grouped_edit_search_keys, data_list = map(list, zip(*sk_data_list))
            output = {}
            output['search_keys'] = grouped_edit_search_keys
            output['update_data'] = data_list
            Trigger.call(self, '%s|%s' % (prefix, search_type), output)
