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


"""Original sidebar configuration order on the packaged XML resources."""
import json
from importlib.resources import files
from pyasm.common import Environment, Container
from pyasm.search import Search, WidgetDbConfig
from pyasm.biz import Project
from pyasm.common.errors import UnsupportedContract
from .widget_config import WidgetConfig, WidgetConfigView


def get_internal_widget_configs(views, base_only=False):
    """Original sidebar XML defaults as metadata; no widget classes are loaded."""
    from pyasm.common import Xml
    defaults = json.loads((files('tactic_stream') / 'compatibility/widget_defaults.json').read_text(encoding='utf-8'))
    base_type = Project.get().get_base_type()
    if base_type and base_type not in defaults:
        raise UnsupportedContract('Widget defaults are not migrated for project type: ' + base_type)
    configs = []
    for kind in ([base_type] if base_only else [base_type, 'DEFAULT']):
        if not kind:
            continue
        xml = Xml(defaults[kind])
        for view in views:
            node = xml.get_node("config/view[@name='%s']" % view) if '@' in view else xml.get_node('config/' + view)
            if node is not None:
                configs.append(WidgetDbConfig(columns={'id': -1, 'view': view, 'config': defaults[kind]}))
    return configs


class SidebarConfig:
    @staticmethod
    def add_internal_config(configs, views):
        configs.extend(get_internal_widget_configs(views))

    @classmethod
    def get_config(cls, config_search_type, view, default=False, personal=False):
        config = None
        configs = []
        login = None
        defined_view = view
        # this is really for the predefined view that shouldn't go to the db
        # otherwise, it is a never ending cycle.
        if default:
            views = [defined_view, 'definition']
            SidebarConfig.add_internal_config(configs, views)

        # special condition for children
        elif view in ['children']:
            defaults = json.loads((files('tactic_stream') / 'compatibility/widget_defaults.json').read_text(encoding='utf-8'))
            config = WidgetConfig.get(xml=defaults['children'], view=defined_view)
            configs.append(config)


        elif view == "definition":
            # look for a definition in the database
            search = Search("config/widget_config")
            search.add_filter("search_type", config_search_type)
            search.add_filter("view", "definition")
            # lower the chance of getting some other definition files
            if personal:
                login = Environment.get_user_name()

            search.add_filter("login", login)

            config = search.get_sobject()
            if config:
                configs.append(config)
            # We should not allow redefinition of a predefined item
            # so it is fine to add internal config for definition
            # then look for a definition in the definition file
            SidebarConfig.add_internal_config(configs, ['definition'])



        else:
            # first look in the database
            search = Search("config/widget_config")
            search.add_filter("search_type", config_search_type)
            search.add_filter("view", view)
            if search.column_exists("priority"):
                search.add_order_by("priority desc")
            config = search.get_sobject()
            if config:
                configs.append(config)

            # then look for a file
            SidebarConfig.add_internal_config(configs, [defined_view])

            logins = []
            if personal:
                logins.append(Environment.get_user_name())

            logins.append(None)
            for login in logins:
                # look for a definition in the database
                search = Search("config/widget_config")
                search.add_filter("search_type", config_search_type)
                search.add_filter("view", "definition")
                # lower the chance of getting some other definition files
                search.add_filter("login", login)

                key = '%s|definition|%s'%(config_search_type, login)
                config = WidgetDbConfig.get_by_search(search, key)
                if config:
                    configs.append(config)


            # then look for a definition in the definition file
            SidebarConfig.add_internal_config(configs, ['definition'])

        # The shared XML editor previews detached records in this request only.
        preview = Container.get('WidgetDbConfig:preview')
        if preview:
            resource = Search('config/widget_config').get_db_resource().get_key()
            for (database, search_type, draft_view), records in preview.items():
                if database != resource or search_type != config_search_type:
                    continue
                configs = [item for item in configs if item.get_view() != draft_view or item.get_id() == -1]
                candidate = WidgetDbConfig.merge_configs(records)
                if candidate:
                    index = next((index for index, item in enumerate(configs) if item.get_view() == draft_view), len(configs))
                    configs.insert(index, candidate)
        widget_config_view = WidgetConfigView(config_search_type, view, configs)

        return widget_config_view
