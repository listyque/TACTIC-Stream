# Copyright (c) 2005, Southpaw Technology. See LICENSE.TACTIC.
"""Headless operations from the original Search Type Manager."""
from pyasm.command import Command, ColumnDropCmd
from pyasm.common import Container, TacticException
from pyasm.web import WebContainer
from pyasm.search import WidgetDbConfig
from pyasm.widget import WidgetConfig


class AlterSearchTypeCbk(Command):
    DEFAULT_VIEW = 'definition'

    def check(self):
        return True

    def execute(self):
        from pyasm.common.errors import UnsupportedContract
        if self.kwargs.get('alter_mode') != 'Remove Column':
            raise UnsupportedContract('Search Type Manager supports Remove Column; other alter modes are not migrated')
        web = WebContainer.get_web()
        column_name = web.get_form_value('column_name')
        search_type = web.get_form_value('target_search_type')
        if not column_name or not search_type:
            raise TacticException('Select a Search Type and column')
        if web.get_form_value('config_constraint'):
            raise UnsupportedContract('Column constraint changes are not migrated')
        Command.execute_cmd(ColumnDropCmd(search_type, column_name))
        widget_config = WidgetDbConfig.get_by_search_type(search_type, 'definition')
        if widget_config:
            config = WidgetConfig.get('definition', xml=widget_config.get_xml_value('config'))
            config.remove_xml_element(column_name)
            widget_config.set_value('config', config.get_xml().to_string())
            widget_config.commit()
            Container.put('WidgetConfigView:config_cache', {})
