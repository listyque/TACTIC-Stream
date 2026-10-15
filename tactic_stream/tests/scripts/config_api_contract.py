"""The same settings/config/subscription calls in original and native TACTIC."""
import ast
import json
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Common, Config, Environment
from pyasm.web.api_xmlrpc import ApiXMLRPC
from pyasm.search import Search
from pyasm.security import Security
from pyasm.web import WidgetSettings


def element(value):
    node = ET.fromstring(value)
    return dict(name=node.get('name'), title=node.get('title'),
                display=node.find('display').get('class') if node.find('display') is not None else None,
                options={item.tag: item.text for item in node.findall('display/*')})


def config(view, login=None):
    search = Search('config/widget_config')
    search.add_filter('search_type', 'contract/config_api')
    search.add_filter('view', view)
    search.add_filter('login', login)
    return search.get_sobject()


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    security = Environment.get_security()
    old_ticket = security._ticket
    security._ticket = Search('sthpw/ticket').get_sobject()
    cmd = Command()
    def execute():
        cmd.get_transaction().set_sync(False)
        api = ApiXMLRPC()
        api.set_protocol('local')
        code = Project.get_project_code()
        ticket = dict(project=code, language='python')
        stype = 'contract/config_api'
        if case.get('bug') == 'personal':
            api.set_config_definition(ticket, stype, 'scope_custom', '<element name="scope_custom" title="Global"/>')
            api.set_config_definition(ticket, stype, 'scope_custom', '<element name="scope_custom" title="Personal"/>', 'admin')
            api.add_config_element(ticket, stype, 'scope', 'global')
            api.add_config_element(ticket, stype, 'scope', 'personal', None, {}, None, {}, {}, 'admin')
            api.update_config(ticket, stype, 'scope', ['personal'], 'admin')
            return dict(personal=config('definition', 'admin') is not None,
                        global_names=config('scope').get_element_names(),
                        personal_names=config('scope', 'admin').get_element_names())
        if case.get('bug') == 'subscription':
            api.subscribe(ticket, 'same_project_key')
            other = case.get('other_project', 'two')
            try:
                Project.set_project(other)
                ticket['project'] = other
                try:
                    api.subscribe(ticket, 'same_project_key')
                    subscribed = True
                except Exception as error:
                    if type(error).__name__ != 'ApiException':
                        raise
                    subscribed = False
            finally:
                Project.set_project(code)
            return dict(other_subscribed=subscribed)
        if case.get('bug') == 'separator':
            api.set_config_definition(ticket, stype, 'new_separator_test')
            return element(api.get_config_definition(ticket, stype, 'definition', 'new_separator_test'))
        if case.get('bug') == 'attribute':
            error_name = None
            try:
                api.add_config_element(ticket, stype, 'table@api', 'first')
                api.add_config_element(ticket, stype, 'table@api', 'second')
                api.update_config(ticket, stype, 'table@api', ['second', 'first'])
            except Exception as error:
                error_name = type(error).__name__
            row = config('table@api')
            return dict(error=error_name, names=row.get_element_names() if row else [])
        assert api.get_widget_setting(ticket, 'config_api_setting') == ''
        assert api.set_widget_setting(ticket, 'config_api_setting', {'text': 'Точный текст', 'values': [0, False]}) is True
        setting = json.loads(api.get_widget_setting(ticket, 'config_api_setting'))
        api.set_widget_setting(ticket, 'config_api_setting', 'second')
        assert api.get_widget_setting(ticket, 'config_api_setting') == 'second'
        WidgetSettings.set_key_values('config_api_setting', ['one', '', 7])
        assert WidgetSettings.get_key_values('config_api_setting') == ['one', '7']
        subscribed = api.subscribe(ticket, 'config_api_key', 'work')
        duplicate = False
        try:
            api.subscribe(ticket, 'config_api_key')
        except Exception as error:
            if type(error).__name__ != 'ApiException':
                raise
            duplicate = True
        removed = api.unsubscribe(ticket, 'config_api_key')
        assert removed['id'] == subscribed['id']
        api.add_interaction(ticket, 'config_api_key', {'text': 'Кириллица', 'flag': False})
        interactions = api.get_interaction_count(ticket, 'config_api_key')
        assert api.get_plugin_dir(ticket, 'missing_plugin') == '/tactic/plugins/missing_plugin'
        assert api.get_plugin_dir(ticket, {'code': 'TACTIC_test', 'rel_dir': 'TACTIC_test-1'}) == '/tactic/builtin_plugins/TACTIC_test-1'
        api.set_config_definition(ticket, stype, 'api_custom', '<element name="api_custom" title="Точное имя"><display class="custom.Cell"><text>O\'Reilly &amp; текст</text></display></element>')
        api.add_config_element(ticket, stype, 'api_view', 'api_custom')
        definition = element(api.get_config_definition(ticket, stype, 'api_view', 'api_custom'))
        builtin = element(api.get_config_definition(ticket, 'SideBarWdg', 'definition', 'new_link'))
        assert api.get_config_definition(ticket, stype, 'api_view', 'missing') == ''
        api.add_config_element(ticket, stype, 'api_view', 'second', 'custom.Other', {}, None, {}, {'title': 'Second'})
        options = {'view': 'second'}
        with patch.object(Common, 'randint', return_value=5):
            generated = api.add_config_element(ticket, stype, 'api_view', 'second', 'custom.Folder', options,
                                               None, {}, {}, None, False, True, True)
        options_preserved = options == {'view': 'second'}
        reordered = element_names(api.update_config(ticket, stype, 'api_view', ['second', 'api_custom']))
        deleted = element_names(api.update_config(ticket, stype, 'api_view', ['api_custom', 'second'], None, ['api_custom']))
        definition_deleted = config('definition').get_element_node('api_custom') is None
        upload = Path(Environment.get_upload_dir())
        upload.mkdir(parents=True, exist_ok=True)
        (upload / 'staged.txt').write_text('staged', encoding='utf-8')
        assert api.clear_upload_dir(ticket) is True and not upload.exists()
        security = Environment.get_security()
        getter = Config.get_value
        query_error = None
        with patch.object(Config, 'get_value', side_effect=lambda category, key, *args, **kwargs: 'true' if (category, key) == ('security', 'enable_fast_query') else getter(category, key, *args, **kwargs)):
            try:
                try:
                    queried = ast.literal_eval(api.fast_query(ticket, 'config/widget_config', [['view', 'api_view']], 1))
                except Exception as error:
                    if type(error).__name__ != 'SecurityException':
                        raise
                    queried = None
                    query_error = type(error).__name__
                security_preserved = Environment.get_security() is security
            finally:
                Environment.set_security(security)
        if case.get('fail'):
            raise ValueError('config API rollback')
        return dict(setting=setting, duplicate=duplicate, subscription=[subscribed['login'], subscribed['category'], removed['message_code']],
                    interactions=interactions, definition=definition, builtin=builtin,
                    generated=generated, options_preserved=options_preserved, reordered=reordered, deleted=deleted,
                    queried=len(queried) if queried is not None else None, query_error=query_error,
                    security_preserved=security_preserved, definition_deleted=definition_deleted)
    cmd.execute = execute
    try:
        return Command.execute_cmd(cmd)
    finally:
        security._ticket = old_ticket
        Environment.set_security(previous)


def element_names(value):
    return [node.get('name') for node in ET.fromstring(value).findall('./*/element')]
