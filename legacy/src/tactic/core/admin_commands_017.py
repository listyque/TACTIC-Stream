"""Original administration commands separated from presentation (0.17).
Bodies are retained from the delivered TACTIC source; see source-provenance-017.json.
Only validated, server-selected arguments reach these classes from native routes.
"""
from pyasm.common import Environment, Common, Xml, jsonloads, Container, TacticException
from pyasm.search import Search, SearchType
from pyasm.security import LoginGroup, LoginInGroup
from pyasm.biz import Project
from pyasm.web import WebContainer
from pyasm.command import Command, CommandException
import six

class GroupAssignCbk(Command):

    def execute(self):

        web = WebContainer.get_web()
        values = self.kwargs.get("values")
        group_names = values.get("group_name")

        search_key = values.get("search_key")[0]
        login = Search.get_by_search_key(search_key)

        # find all the groups that this user current is in
        login_in_groups = LoginInGroup.get_by_login_name(login.get_code())
        current_groups = set()
        for x in login_in_groups:
            if x.get_value("login_group") not in group_names:
                if x.get_value('login_group') == 'admin':
                    current_groups.add( x.get_value("login_group") )
                else:
                    x.delete()
            else:
                current_groups.add( x.get_value("login_group") )

        for group_name in group_names:
            if not group_name:
                continue

            # don't add again
            if group_name in current_groups:
                continue

            sobject = SearchType.create("sthpw/login_in_group")
            sobject.set_value("login", login.get_code() )
            sobject.set_value("login_group", group_name)
            sobject.commit()


        project = Project.get()
        project_code = project.get_code()

        new_groups = values.get("new_group")
        for new_group in new_groups:
            if not new_group:
                continue

            # make sure the group doesn't already exist
            #login_group = LoginGroup.get_by_login_group(new_group)

            project_included = False
            user_defined_project_code = ""
            original_new_group = new_group
            is_project_specific = False
            if self.kwargs.get("checked") in [True, "true", "True"]:
                is_project_specific = True

            if new_group.find("/") == -1:
                title = new_group
                new_group = "%s/%s" % (project_code, new_group)
            else:
                parts = new_group.split("/")
                title = parts[1]
                user_defined_project_code = parts[0]
                project_included = True

            new_group = Common.get_filesystem_name(new_group)

            group = SearchType.create("sthpw/login_group")

            # the following sections contains the 4 cases possible when creating a new group
            # through the popup
            
            # if the input is (project/name) and (not project specific)
            if not is_project_specific and project_included:
                
                # Raise exception because it's contradictory data
                raise TacticException('''You've given a project code while declaring 
                    the group not project specific. You can either not use the format 
                    "project_code/group_name", or check the "Project specific" checkbox.''')

            # if the input is (project/name) and (project specific)
            elif is_project_specific and project_included:

                # first check is the user_defined_project_code is actually a project
                # if it is, then set that as the project code. If not, don't set anything

                user_defined_project = Project.get_by_code(user_defined_project_code)

                if user_defined_project:
                    group.set_value("project_code", user_defined_project_code)
                else:
                    raise TacticException('''The project code that you've given doesn't exist.
                        Please choose an existing project code. Note: the format is
                        "project_code/group_name".''')
                group.set_value("login_group", original_new_group)

            # if the input is (name) and (not project specific)
            elif not is_project_specific and not project_included:
                group.set_value("login_group", title)

            # if the input is (name) and (project specific)
            else:
                group.set_value("project_code", project_code)
                group.set_value("login_group", new_group)

            group.set_value("description", title)
            group.commit()

            self.info = {
                'close_popup': False
            }


class ProjectSecurityCbk(Command):
    def execute(self):

        search_keys = self.kwargs.get("search_keys")
        update_data = self.kwargs.get("update_data")
        if isinstance(update_data, six.string_types):
            update_data = jsonloads(update_data)

        extra_data = self.kwargs.get("extra_data")
        if isinstance(extra_data, six.string_types):
            extra_data = jsonloads(extra_data)


        builders = {}
        for search_key,data,extra in zip(search_keys, update_data, extra_data):

            if extra:
                is_all = extra.get("is_all")
            else:
                is_all = False

            if is_all:
                project_code = "*"
            else:
                project = Search.get_by_search_key(search_key)
                project_code = project.get_code()

            for group_name, is_insert in data.items():
                group_name = group_name.lstrip("_")

                group = LoginGroup.get_by_code(group_name)
                builder = builders.get(group_name)
                if not builder:
                    builder = SecurityBuilder(group=group)
                    builders[group_name] = builder

                if is_insert == "true":
                    builder.add_project(project_code)
                else:
                    builder.remove_project(project_code)

        for group_name, builder in builders.items():
            group_name = group_name.lstrip("_")
            group = LoginGroup.get_by_code(group_name)
            access_rules = builder.to_string()
            group.set_value("access_rules", access_rules)
            group.commit()


class SearchTypeSecurityCbk(Command):
    def execute(self):

        search_keys = self.kwargs.get("search_keys")
        update_data = self.kwargs.get("update_data")
        if isinstance(update_data, six.string_types):
            update_data = jsonloads(update_data)

        extra_data = self.kwargs.get("extra_data")
        if isinstance(extra_data, six.string_types):
            extra_data = jsonloads(extra_data)


        project = Project.get()
        project_code = project.get_code()

        builders = {}
        for search_key,data,extra in zip(search_keys, update_data, extra_data):

            if extra:
                is_all = extra.get("is_all")
            else:
                is_all = False

            if is_all:
                search_type = "*"
            else:
                search_type_obj = Search.get_by_search_key(search_key)
                search_type = search_type_obj.get_value("search_type")

            for group_name, is_insert in data.items():
                group_name = group_name.lstrip("_")

                group = LoginGroup.get_by_code(group_name)
                builder = builders.get(group_name)
                if not builder:
                    builder = SecurityBuilder(group=group)
                    builders[group_name] = builder

                if is_insert == "true":
                    builder.add_search_type(search_type, project_code=project_code)
                else:
                    builder.remove_search_type(search_type, project_code=project_code)

        for group_name, builder in builders.items():
            group_name = group_name.lstrip("_")
            group = LoginGroup.get_by_code(group_name)
            access_rules = builder.to_string()
            group.set_value("access_rules", access_rules)
            group.commit()


class GearMenuSecurityCbk(Command):
    def execute(self):

        search_keys = self.kwargs.get("search_keys")
        update_data = self.kwargs.get("update_data")
        if isinstance(update_data, six.string_types):
            update_data = jsonloads(update_data)

        extra_data = self.kwargs.get("extra_data")

        if isinstance(extra_data, six.string_types):
            extra_data = jsonloads(extra_data)

        project = Project.get()
        project_code = project.get_code()

        builders = {}
        for search_key,data,extra in zip(search_keys, update_data, extra_data):
            
            label = extra.get("label")
            submenu = extra.get("submenu")
            if submenu == "ALL MENU ITEMS":
                submenu = '*'

            for group_name, is_insert in data.items():
                group_name = group_name.lstrip("_")

                group = LoginGroup.get_by_code(group_name)
                builder = builders.get(group_name)
                if not builder:
                    builder = SecurityBuilder(group=group)
                    builders[group_name] = builder

                if is_insert == "true":
                    builder.add_gear_menu(submenu, label, project_code=project_code)
                else:
                    builder.remove_gear_menu(submenu, label, project_code=project_code)

        for group_name, builder in builders.items():
            group_name = group_name.lstrip("_")
            group = LoginGroup.get_by_code(group_name)
            access_rules = builder.to_string()
            group.set_value("access_rules", access_rules)
            group.commit()


class LinkSecurityCbk(Command):
    def execute(self):

        search_keys = self.kwargs.get("search_keys")
        update_data = self.kwargs.get("update_data")
        if isinstance(update_data, six.string_types):
            update_data = jsonloads(update_data)

        extra_data = self.kwargs.get("extra_data")
        if isinstance(extra_data, six.string_types):
            extra_data = jsonloads(extra_data)

        project = Project.get()
        project_code = project.get_code()

        builders = {}
        for search_key,data,extra in zip(search_keys, update_data, extra_data):

            link = extra.get("link")

            for group_name, is_insert in data.items():
                group_name = group_name.lstrip("_")

                group = LoginGroup.get_by_code(group_name)
                builder = builders.get(group_name)
                if not builder:
                    builder = SecurityBuilder(group=group)
                    builders[group_name] = builder

                if is_insert == "true":
                    builder.add_link(link, project_code=project_code)
                else:
                    builder.remove_link(link, project_code=project_code)



        for group_name, builder in builders.items():
            group_name = group_name.lstrip("_")
            group = LoginGroup.get_by_code(group_name)
            access_rules = builder.to_string()
            group.set_value("access_rules", access_rules)
            group.commit()


class ProcessSecurityCbk(Command):

    def use_project(self):
        return True

    def use_pipeline(self):
        return False

    def execute(self):

        search_keys = self.kwargs.get("search_keys")
        update_data = self.kwargs.get("update_data")
        if isinstance(update_data, six.string_types):
            update_data = jsonloads(update_data)

        extra_data = self.kwargs.get("extra_data")
        if isinstance(extra_data, six.string_types):
            extra_data = jsonloads(extra_data)

        project = Project.get()
        if self.use_project():
            project_code = project.get_code()
        else:
            project_code = None

        builders = {}
        for search_key,data,extra in zip(search_keys, update_data, extra_data):

            if extra:
                is_all = extra.get("is_all")
                #st = extra.get("search_type")
            else:
                is_all = False

            pipeline_code = ""
            if is_all:
                process = "*"
                pipeline_code = "*"
            else:
                process_sobj = Search.get_by_search_key(search_key)
                process = process_sobj.get_value("process")
                if self.use_pipeline():
                    pipeline_code = process_sobj.get_value("pipeline_code")

            for group_name, is_insert in data.items():
                group_name = group_name.lstrip("_")

                group = LoginGroup.get_by_code(group_name)
                builder = builders.get(group_name)
                if not builder:
                    builder = SecurityBuilder(group=group)
                    builders[group_name] = builder

                if is_insert == "true":
                    builder.add_process(process, project_code=project_code, pipeline_code=pipeline_code)
                else:
                    builder.remove_process(process, project_code=project_code, pipeline_code=pipeline_code)


        for group_name, builder in builders.items():
            group_name = group_name.lstrip("_")
            group = LoginGroup.get_by_code(group_name)
            access_rules = builder.to_string()
            group.set_value("access_rules", access_rules)
            group.commit()


class TaskSecurityCbk(ProcessSecurityCbk):

    def use_project(self):
        return False

    def use_pipeline(self):
        return True


class SecurityBuilder(object):

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        group = self.kwargs.get("group")
        if group:
            self.xml = group.get_xml_value("access_rules")

        else:
            self.xml = Xml()
            self.xml.read_string("<rules/>")

        assert self.xml

        self.root = self.xml.get_root_node()


    def get_xml(self):
        return self.xml


    def to_string(self):
        return self.xml.to_string()


    def add_project(self, project_code, access="allow"):
        rule = self.xml.create_element("rule")
        self.xml.set_attribute(rule, "group", "project")
        self.xml.set_attribute(rule, "code", project_code)
        self.xml.set_attribute(rule, "access", access)
        self.xml.append_child(self.root, rule)

    def remove_project(self, project_code):
        nodes = self.xml.get_nodes("rules/rule[@group='project']")
        for node in nodes:
            if self.xml.get_attribute(node, 'code') == project_code:
                self.xml.remove_child(self.root, node)





    def add_gear_menu(self, submenu, label, access="allow", project_code=None):
        if project_code:
            nodes = self.xml.get_nodes("rules/rule[@group='gear_menu' and @project='%s']" % project_code)

        else:
            nodes = self.xml.get_nodes("rules/rule[@group='gear_menu']")

        submenus = [self.xml.get_attribute(node, 'submenu') for node in nodes]
        labels = [self.xml.get_attribute(node, 'label') for node in nodes]

        if label not in labels:
            rule = self.xml.create_element("rule")
            self.xml.set_attribute(rule, "group", "gear_menu")
            self.xml.set_attribute(rule, "submenu", submenu)
            self.xml.set_attribute(rule, "label", label)
            if project_code:
                self.xml.set_attribute(rule, "project", project_code)
            self.xml.set_attribute(rule, "access", access)
            self.xml.append_child(self.root, rule)
            
    def remove_gear_menu(self, submenu, label, project_code=None):
        if project_code:
            nodes = self.xml.get_nodes("rules/rule[@group='gear_menu' and @project='%s']" % project_code)

        else:
            nodes = self.xml.get_nodes("rules/rule[@group='gear_menu']")
        for node in nodes:
            if self.xml.get_attribute(node, 'label') == label:
                self.xml.remove_child(self.root, node)
    


    def add_link(self, link, access="allow", project_code=None):
        if project_code:
            nodes = self.xml.get_nodes("rules/rule[@group='link' and @project='%s']" % project_code)
        else:
            nodes = self.xml.get_nodes("rules/rule[@group='link']")
        links = [self.xml.get_attribute(node, 'element') for node in nodes] 

        if link not in links:
            rule = self.xml.create_element("rule")
            self.xml.set_attribute(rule, "group", "link")
            self.xml.set_attribute(rule, "element", link)
            if project_code:
                self.xml.set_attribute(rule, "project", project_code)
            self.xml.set_attribute(rule, "access", access)
            self.xml.append_child(self.root, rule)


    def remove_link(self, link, project_code=None):
        if project_code:
            nodes = self.xml.get_nodes("rules/rule[@group='link' and @project='%s']" % project_code)
        else:
            nodes = self.xml.get_nodes("rules/rule[@group='link']")

        for node in nodes:
            if self.xml.get_attribute(node, 'element') == link:
                self.xml.remove_child(self.root, node)



    def add_process(self, process, access="allow", project_code=None, pipeline_code=None):
        '''check before adding a new node since the user can uncheck and check again'''

        pipeline_code_expr = ''
        if pipeline_code:
            pipeline_code_expr = "and @pipeline='%s'"%pipeline_code

        project_code_expr = ''
        if project_code:
            project_code_expr = "and @project='%s'"%project_code

        check_node = self.xml.get_node("rules/rule[@group='process' and @process='%s' %s %s]" % (process, pipeline_code_expr, project_code_expr))
        if check_node is None:
            rule = self.xml.create_element("rule")
            self.xml.set_attribute(rule, "group", "process")
            self.xml.set_attribute(rule, "process", process)
            if project_code:
                self.xml.set_attribute(rule, "project", project_code)
            if pipeline_code:
                self.xml.set_attribute(rule, "pipeline", pipeline_code)
            self.xml.set_attribute(rule, "access", access)
            self.xml.append_child(self.root, rule)


    def remove_process(self, process, project_code=None, pipeline_code=None):
        pipeline_code_expr = ''
        if pipeline_code:
            pipeline_code_expr = "and @pipeline='%s'"%pipeline_code
        
        if project_code:
            nodes = self.xml.get_nodes("rules/rule[@group='process' and @project='%s' %s]" % (project_code, pipeline_code_expr))
        else:
            # for backward comaptibilty when the concept of @pipeline doesn't exist at all 
            check_node = self.xml.get_node("rules/rule[@pipeline]")
            if check_node is not None:
                nodes = self.xml.get_nodes("rules/rule[@group='process' %s]" % pipeline_code_expr)
            else:
                nodes = self.xml.get_nodes("rules/rule[@group='process']")
                
        if not nodes and process =='*':
            nodes = self.xml.get_nodes("rules/rule[@group='process' and @process='*']")

        for node in nodes:
            if self.xml.get_attribute(node, 'process') == process:
                self.xml.remove_child(self.root, node)




    def add_search_type(self, search_type, access="allow", project_code=None):
        rule = self.xml.create_element("rule")
        self.xml.set_attribute(rule, "group", "search_type")
        self.xml.set_attribute(rule, "code", search_type)
        if project_code:
            self.xml.set_attribute(rule, "project", project_code)
        self.xml.set_attribute(rule, "access", access)
        self.xml.append_child(self.root, rule)


    def remove_search_type(self, search_type, project_code=None):
        if project_code:
            nodes = self.xml.get_nodes("rules/rule[@group='search_type' and @project='%s']" % project_code)
        else:
            nodes = self.xml.get_nodes("rules/rule[@group='search_type']")

        for node in nodes:
            if self.xml.get_attribute(node, 'code') == search_type:
                self.xml.remove_child(self.root, node)




    def add_builtin(self):
        pass


class ColumnEditCbk(Command):

    def execute(self):

        search_type = self.kwargs.get("search_type")
        column_info = SearchType.get_column_info(search_type)

        values = self.kwargs.get("values")

        # get the definition config for this search_type
        from pyasm.search import WidgetDbConfig
        config = WidgetDbConfig.get_by_search_type(search_type, "definition")
        if not config:
            config = SearchType.create("config/widget_config")
            config.set_value("search_type", search_type)
            config.set_value("view", "definition")
            config.commit()
            config._init()


        # add to the edit definition 
        edit_config = WidgetDbConfig.get_by_search_type(search_type, "edit_definition")
        if not edit_config:
            edit_config = SearchType.create("config/widget_config")
            edit_config.set_value("search_type", search_type)
            edit_config.set_value("view", "edit_definition")
            edit_config.commit()
            edit_config._init()


        for data in values:

            name = data.get("name")
            name = name.strip()
            if name == '':
                continue

            try:
                name.encode('ascii')
            except UnicodeEncodeError:
                raise TacticException('Column name needs to be in English. Non-English characters can be used in Title when performing [Edit Column Definition] afterwards.')


            if column_info.get(name):
                raise CommandException("Column [%s] is already defined" % name)

            format = data.get("format")
            fps = data.get("fps")
            data_type = data.get("data_type")

            from pyasm.command import ColumnAddCmd
            cmd = ColumnAddCmd(search_type, name, data_type)
            cmd.execute()
            #(self, search_type, attr_name, attr_type, nullable=True):


            class_name = 'tactic.ui.table.FormatElementWdg'
            options = {
                'format': format,
                'type': data_type,
                'fps': fps
            }


            # add a new widget to the definition
            config.append_display_element(name, class_name, options=options)



            edit_class_name = 'TextWdg'
            edit_options = {}


            # add a new widget to the definition
            edit_config.append_display_element(name, edit_class_name, options=edit_options)

        config.commit_config()
        edit_config.commit_config()


        # views to add it to
        table_views = []
        edit_views = []



class UserSecurityCbk(Command):
    def execute(self):

        search_keys = self.kwargs.get("search_keys")
        update_data = self.kwargs.get("update_data")
        if isinstance(update_data, six.string_types):
            update_data = jsonloads(update_data)

        extra_data = self.kwargs.get("extra_data")
        if isinstance(extra_data, six.string_types):
            extra_data = jsonloads(extra_data)


        # get all of the login for the given groups
        search = Search("sthpw/login_in_group")
        #search.add_filters("login_group", group_names)
        login_in_group_objs = search.get_sobjects()
        login_data = {}
        for login_in_group in login_in_group_objs:
            group = login_in_group.get_value("login_group")
            login = login_in_group.get_value("login")
            data = login_data.get(login)
            if not data:
                data = set()
                login_data[login] = data
            data.add(group)

        # Add / Remove users from group
        builders = {}
        for search_key,data,extra in zip(search_keys, update_data, extra_data):

            login_obj = Search.get_by_search_key(search_key)
            login = login_obj.get_value("login")

            cur_group_names = login_data.get(login)
            if not cur_group_names:
                cur_group_names = set()

            for item in data:
                item = item.lstrip("_")
                if item in cur_group_names:
                    login_obj.remove_from_group(item)
                else:
                    login_obj.add_to_group(item)
