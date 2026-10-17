# Copyright (c) 2005, Southpaw Technology. See LICENSE.TACTIC.
"""TACTIC Project and ProjectType, both derived from the search.SObject base."""
from pyasm.search.search import Search, SObject, _context
from pyasm.common import Common, Config


class Project(SObject):
    SEARCH_TYPE = "sthpw/project"

    @classmethod
    def get_full_search_type(cls, search_type, project_code=None, project=None):
        from pyasm.search.search import SearchType
        if isinstance(search_type, str):
            if search_type.find("?") == -1:
                base_key = search_type
            else:
                # if there is a project, just use it
                return search_type
        else:
            base_key = search_type.get_base_key()

        if base_key.startswith("sthpw/"):
            full_key = base_key
            return full_key



        if project_code:
            code = project_code
        elif project:
            code = project.get_code()
        else:
            # get the current project
            #code = Project.get_global_project_code()
            search_type_obj = SearchType.get(base_key)
            code = search_type_obj.get_database()



        # NOTE: if someone expliclity set the Project.set('sthpw') before this, 
        # it will affect the full key of this sobject
        # prevent sthpw projects from having a "project=" at the end
        if code in ["sthpw", "admin"]:
            full_key = base_key
        else:
            full_key = "%s?project=%s" % (base_key, code)
        return full_key

    @classmethod
    def set_project(cls, project_code):
        from dataclasses import replace
        from pyasm.security.security import _require_admin
        if project_code == cls.get_project_code():
            return
        from pyasm.common import Container
        attachment = Container.get('Chat:attachment')
        profile = Container.get('UserProfile:writing')
        if profile and profile['avatar']: attachment = profile
        if not attachment or project_code not in ('sthpw', attachment['project']):
            _require_admin()
        if cls.get_by_code(project_code) is None:
            raise LookupError('Unknown or retired project: %s' % project_code)
        # Keep the request's Security, connection pool and Transaction; changing
        # projects must not create an independent request or commit anything.
        _context.set(replace(_context.get(), project=project_code))
        from pyasm.command import Trigger
        Trigger.clear_db_cache()

    @staticmethod
    def get_project_code():
        return _context.get().project

    @staticmethod
    def get_project_name():
        return Project.get().get_code()

    @classmethod
    def get_by_code(cls, code):
        return Search.get_by_code(cls.SEARCH_TYPE, code, show_retired=False)

    @classmethod
    def get_default_project(cls):
        return Config.get_value('install', 'default_project')

    @classmethod
    def get_all_projects(cls):
        search = Search(cls.SEARCH_TYPE)
        search.add_filters('code', ['admin', 'sthpw'], op='not in')
        return search.get_sobjects()

    @classmethod
    def get(cls):
        return cls.get_by_code(cls.get_project_code())

    @classmethod
    def get_by_search_type(cls, search_type):
        from pyasm.search import SearchType
        assert not isinstance(search_type, SearchType)
        project_code = cls.extract_project_code(search_type)
        return cls.get() if project_code == '__NONE__' else cls.get_by_code(project_code)

    @classmethod
    def extract_project_code(cls, search_type):
        from pyasm.search import SearchKey, SearchType
        base_search_type, data = SearchKey._get_data(search_type)
        project_code = data.get("project")
        if project_code == None:
            if search_type.startswith('sthpw/'):
                return 'sthpw'
            # this is specifically for project-specific sType
            
            search_type_obj = SearchType.get(search_type)
            database = search_type_obj.get_value("database")
            if database != "{project}":
                project_code = database
            else:
                # get the global project code
                project_code = Project.get_project_code()

            #project_code = cls.get_global_project_code()
        return project_code

    def get_database_name(self):
        # Read raw data to avoid recursion through project database lookup.
        database_name = self.get_data().get('database') or self.get_code()
        return 'sthpw' if database_name == 'admin' else database_name

    def database_exists(self):
        resource = self.get_project_db_resource()
        return resource.get_database_impl().database_exists(resource)

    def get_project_db_resource(self, database=None):
        from pyasm.search.sql import DbResource
        database = database or self.get_database_name()
        code = self.get_value('db_resource', no_exception=True) if database != 'sthpw' else None
        if DbResource.is_instance(code):
            return code
        if code:
            return DbResource.get_by_code(code.strip(), database)
        return DbResource.get_default(database)

    @classmethod
    def get_db_resource_by_search_type(cls, search_type):
        from pyasm.search.sql import DbResource
        if search_type.startswith("sthpw/"):
            return DbResource.get_default("sthpw")
        context = _context.get()
        from pyasm.search.keys import breakup_search_type
        definition, database, _ = context.store.resolve(search_type, context.project)
        if definition['database'] == '{project}':
            code = breakup_search_type(search_type).get('project') or context.project
            project = cls.get_by_code(code)
            if project is None or project.is_retired():
                raise LookupError('Unknown or retired project')
            return project.get_project_db_resource()
        return DbResource.get_default(database)

    def get_base_type(self):
        if self.get_code() == "admin":
            return "admin"
        project_type = Search.get_by_code(ProjectType.SEARCH_TYPE, self.get_value("type"))
        return project_type.get_type() if project_type else ""


    # repo handling
    def get_project_repo_handler(project_code=None):
        if not project_code:
            project = Project.get()
        else:
            project = Project.get_by_code(project_code)

        repo_handler_cls = project.get_value("repo_handler_cls", no_exception=True)

        if not repo_handler_cls and project.get_project_type():
            repo_handler_cls = project.get_project_type().get_value("repo_handler_cls", no_exception=True)


        if not repo_handler_cls:
            repo_handler_cls = "pyasm.biz.BaseRepoHandler"

        repo_handler = Common.create_from_class_path(repo_handler_cls)

        return repo_handler
    get_project_repo_handler = staticmethod(get_project_repo_handler)


    # sobject code naming
    def get_code_naming(sobject,code):
        '''Gets the code naming object for the current project'''
        project = Project.get()
        code_naming_cls = project.get_value("code_naming_cls")
        if code_naming_cls == "":
            code_naming_cls = "pyasm.biz.CodeNaming"

        naming = Common.create_from_class_path(code_naming_cls, \
            [sobject,code] )
        return naming
    get_code_naming = staticmethod(get_code_naming)


    # file naming
    def get_file_naming(cls, sobject=None, project=None):
        '''Gets the file naming object for the current project'''
        return cls.get_naming("file", sobject, project)
    get_file_naming = classmethod(get_file_naming)

    def get_dir_naming(cls, sobject=None, project=None):
        '''Gets the directory naming object for the current project'''
        return cls.get_naming("dir", sobject, project)
    get_dir_naming = classmethod(get_dir_naming)


    
    def get_naming(cls, naming_type, sobject=None, project=None):
        '''get a certain type of naming determined by type of naming'''

        naming_cls = ""
        
        # this import statement is needed for running Batch
        from pyasm.biz import Project
        if not project:
            if sobject:
                project = sobject.get_project()
            else:
                project = Project.get()
       

        if project:
            naming_cls = project.get_value("%s_naming_cls" % naming_type, no_exception=True)
            if not naming_cls and project.get_project_type():
                naming_cls = project.get_project_type().get_value("%s_naming_cls" % naming_type, no_exception=True)



        # if none is defined, use defaults
        if not naming_cls:
            # TODO: this should probably be stored somewhere else
            if naming_type == "file":
                naming_cls = "pyasm.biz.FileNaming"
            elif naming_type == "dir":
                naming_cls = "pyasm.biz.DirNaming"
            elif naming_type == "node":
                from pyasm.common.errors import UnsupportedContract
                raise UnsupportedContract('Deprecated production node naming is excluded')
       
        naming = Common.create_from_class_path(naming_cls)
        return naming
    get_naming = classmethod(get_naming)







    # directory functions for the project
    def get_project_web_dir(sobject,snapshot,file_type=None,file_object=None):
        return Project._get_dir("http", sobject,snapshot,file_type,file_object=file_object)
    get_project_web_dir = staticmethod(get_project_web_dir)

    def get_project_lib_dir(sobject,snapshot,file_type=None, create=False, file_object=None, dir_naming=None):
        return Project._get_dir("file", sobject,snapshot,file_type, create, file_object, dir_naming=dir_naming)
    get_project_lib_dir = staticmethod(get_project_lib_dir)

    def get_project_env_dir(sobject,snapshot,file_type=None):
        return Project._get_dir("env", sobject,snapshot,file_type)
    get_project_env_dir = staticmethod(get_project_env_dir)

    def get_project_client_lib_dir(sobject,snapshot,file_type=None, create=False, file_object=None, dir_naming=None):
        return Project._get_dir("client_lib", sobject,snapshot,file_type, create, file_object, dir_naming=dir_naming)
    get_project_client_lib_dir = staticmethod(get_project_client_lib_dir)


    # DEPRECATED: use get_project_local_repo_dir
    def get_project_local_dir(sobject,snapshot,file_type=None):
        #return Project._get_dir("local", sobject,snapshot,file_type)
        return Project._get_dir("local_repo", sobject,snapshot,file_type)
    get_project_local_dir = staticmethod(get_project_local_dir)

    def get_project_local_repo_dir(sobject,snapshot,file_type=None,file_object=None):
        return Project._get_dir("local_repo", sobject,snapshot,file_type, file_object=file_object)
    get_project_local_repo_dir = staticmethod(get_project_local_repo_dir)




    def get_project_sandbox_dir(sobject,snapshot,file_type=None):
        return Project._get_dir("sandbox", sobject,snapshot,file_type)
    get_project_sandbox_dir = staticmethod(get_project_sandbox_dir)

    def get_sandbox_base_dir(sobject, decrement=0):
        return Project._get_base_dir("sandbox", sobject, decrement=decrement)
    get_sandbox_base_dir = staticmethod(get_sandbox_base_dir)

    def get_project_remote_web_dir(sobject,snapshot,file_type=None):
        return Project._get_dir("remote", sobject,snapshot,file_type)
    get_project_remote_web_dir = staticmethod(get_project_remote_web_dir)

    def get_project_relative_dir(sobject,snapshot,file_type=None, create=False, file_object=None, dir_naming=None):
        return Project._get_dir("relative", sobject,snapshot,file_type, create, file_object, dir_naming=dir_naming)
    get_project_relative_dir = staticmethod(get_project_relative_dir)



    def _get_dir(protocol,sobject,snapshot,file_type=None, create=False, file_object=None, dir_naming=None):

        dir_naming_expr = dir_naming

        from .snapshot import Snapshot, SObjectNotFoundException
        if isinstance(sobject,Snapshot):
            snapshot = sobject
            sobject = snapshot.get_sobject()

        dir_naming = Project.get_dir_naming(sobject)
        dir_naming.set_sobject(sobject)
        dir_naming.set_snapshot(snapshot)
        dir_naming.set_file_type(file_type)
        dir_naming.set_file_object(file_object)
        dir_naming.set_naming(dir_naming_expr)
        dir_naming.set_create(create)
        dir_naming.set_protocol(protocol)
        dirname = dir_naming.get_dir()
        from pyasm.common import Container, Environment
        attachment = Container.get('Chat:attachment')
        profile = Container.get('UserProfile:writing')
        if profile and profile['avatar']: attachment = dict(profile, message_code=profile['code'])
        if attachment and protocol == 'file' and snapshot and snapshot.get_value('search_type') == ('sthpw/login' if profile and profile['avatar'] else 'sthpw/message') and snapshot.get_value('search_code') == attachment['message_code']:
            from pathlib import Path
            path = Path(dirname).resolve()
            if not any(path.is_relative_to(Path(root).resolve()) for root in Environment.get_asset_dirs().values()):
                from pyasm.common.errors import SecurityException
                raise SecurityException('Chat attachment naming must stay in its repository')
            attachment['paths'].add(str(path))
        
        return dirname
    _get_dir = staticmethod(_get_dir)


    def _get_base_dir(protocol, sobject, decrement=0):
        '''decrement is the number of levels it tries to go up the directory'''
        snapshot = None
        from .snapshot import Snapshot
        if isinstance(sobject,Snapshot):
            snapshot = sobject

            # try to get the parent, but protect against dangling snapshots
            from .snapshot import SObjectNotFoundException
            try:
                sobject = snapshot.get_sobject()
            except SObjectNotFoundException as e:
                pass
        
        dir_naming = Project.get_dir_naming(sobject)
        dir_naming.set_sobject(sobject)
        dir_naming.set_snapshot(snapshot)
        dir_naming.set_protocol(protocol)

        """
        dirs = dir_naming.get_base_dir()
        dirs = dir_naming.get_default(dirs)
        dirs = '/'.join(dirs).split('/')
        """
        full_dirs = dir_naming.get_dir().split('/')
        full_dirs = full_dirs[0:len(full_dirs)-decrement]
        return '/'.join(full_dirs)

    _get_base_dir = staticmethod(_get_base_dir)

    def get_project_type(self):
        return ProjectType.get_by_code(self.get_value('type'))

    def get_initials(self):
        return self.get_value('initials') or self.get_code().upper()

    def has_table(self, search_type):
        from pyasm.search import SearchType
        if isinstance(search_type, str):
            search_type = SearchType.get(search_type)
        table = search_type.get_table()
        if not table:
            return False
        resource = self.get_project_db_resource()
        return resource.get_database_impl().table_exists(resource, table)

    def get_search_types(self, include_sthpw=False, include_config=False, include_multi_project=False):
        # Original namespace/database selection; do not reuse a result across
        # different include flags or hide failures as an absent table.
        search = Search('sthpw/search_object')
        namespaces = [self.get_code(), self.get_value('type')]
        if include_sthpw:
            namespaces.append('sthpw')
        if include_config:
            namespaces.append('config')
        if include_multi_project:
            if not include_config:
                search.add_filter('namespace', 'config', op='!=')
            if not include_sthpw:
                search.add_filter('namespace', 'sthpw', op='!=')
            search.add_op('begin')
            search.add_filter('database', '{project}')
        search.add_filters('namespace', namespaces)
        if include_multi_project:
            search.add_op('or')
        search.add_order_by('search_type')
        return [item for item in search.get_sobjects()
                if (item.get_value('namespace') == 'sthpw'
                    and 'custom_property' not in item.get_value('search_type'))
                or self.has_table(item)]


class ProjectType(SObject):
    SEARCH_TYPE = "sthpw/project_type"

    def get_type(self):
        return self.get_value("type")


# DEPRECATED
class Repo(SObject):
    SEARCH_TYPE = "sthpw/repo"

    def get_handler(self):
        handler_class = self.get_value("handler")
        repo_handler = Common.create_from_class_path(handler_class)
        return repo_handler
        
class RemoteRepo(SObject):
    SEARCH_TYPE = "sthpw/remote_repo"

    def get_by_login(login):
        search = Search(RemoteRepo.SEARCH_TYPE)
        search.add_filter('login', login)
        repo = RemoteRepo.get_by_search(search, login)
        return repo

    get_by_login = staticmethod(get_by_login)


