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

__all__ = ['BaseUpgrade']


import inspect, re

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.search import Search, DbContainer, SqlException, Transaction
from pyasm.common import Base, Common, Container

import six



class BaseUpgrade(Command):


    def is_undoable(cls):
        return False
    is_undoable = classmethod(is_undoable)


    def __init__(self):
        self.upgrade_method = None
        self.to_version = 0
        self.is_forced = False
        self.quiet = False
        self.is_confirmed = False
        self.commit_now = True
        self.upgrade_class = None
        self.sqlite_managed = None
        super(BaseUpgrade, self).__init__()
    
    def set_project(self, project_code):
        self.project_code = project_code
        Project.set_project(project_code)

    def set_upgrade_method(self, method):
        ''' this is the name of the method for the current upgrade instance'''
        if not isinstance(method, six.string_types):
            raise TacticException('method should be a string')
        self.upgrade_method = method 

    def set_upgrade_class(self, class_name):
        self.upgrade_class = class_name

    def set_to_version(self, version):
        self.to_version = version

    def set_forced(self, forced):
        self.is_forced = forced

    def set_quiet(self, quiet):
        self.quiet = quiet

    def set_confirmed(self, is_confirmed):
        self.is_confirmed = is_confirmed

    def set_commit(self, commit):
        self.commit_now = commit

    def execute(self):
        assert self.project_code

        # get the project and find out the date of the last update of the
        # database
        project = Project.get()
        self.version_update = project.get_value("last_version_update", no_exception=True)
        # This is a fix for versions that contains underscores, versions should be decimals
        self.version_update = (self.version_update or "").replace("_", ".")
        
        if self.sqlite_managed and self.sqlite_managed.get("repair_from"):
            # The old runner stamped last_version_update even when SQL failed.
            # Only the explicit, staged managed repair may replay from baseline.
            self.version_update = self.sqlite_managed["repair_from"]
        if not self.version_update:
            self.version_update = "2.5.0.v01"

        if Common.IS_Pv3:
            members = inspect.getmembers(self.__class__, predicate=inspect.isfunction)
        else:
            members = inspect.getmembers(self.__class__, predicate=inspect.ismethod)
        methods = []
        critical_methods = []
        for name, member in members:
            if name.startswith('upgrade_v'):
                methods.append((name, member))
            if name.startswith('critical_v'):
                critical_methods.append((name, member))

        methods.sort()

        # add the critical methods at the beginning
        critical_methods.reverse()
        for critical_method in critical_methods:
            methods.insert(0, critical_method)


        # make sure critical methods are run first
        methods.sort()
        for name, method in methods:
            if name.startswith("critical"):
                method_version = re.sub(r'critical_v(\w*)_(\d{3}(\w)?)$', '\\1', name) 
            else:
                method_version = re.sub(r'upgrade_v(\w*)_(\d{3}(\w)?)$', '\\1', name) 

            method_version = method_version.replace('_', '.')
            if self.is_forced:
                if not (self.version_update <= method_version <= self.to_version):
                    continue
            elif not (self.version_update < method_version <= self.to_version):
                    continue
            if not self.quiet:
                print("Running upgrade for [%s]..." %name)

            self.run_method(name, method)



    def get_database_type(self):
        project = Project.get_by_code(self.project_code)
        db_resource = project.get_project_db_resource()
        db = DbContainer.get(db_resource)
        return db.get_database_type()

    def run_method(self, name, method):
            if self.sqlite_managed is not None:
                return self._run_managed_sqlite_method(name, method)
            try:
                #upgrade = eval( '%s()' %self.__class__.__name__)
                upgrade = BaseUpgrade()
            except NameError:
                print("Failed to import upgrade script for %s" %self.__class__.__name__ )
                return
            # substitute the function of 'execute' method with the
            # upgrade script
            Common.add_func_to_class(method, upgrade, upgrade.__class__, 'execute')

            upgrade.set_project(self.project_code)
            upgrade.set_upgrade_class(self.__class__.__name__)
            upgrade.set_upgrade_method(name)

            upgrade.set_quiet(self.quiet)
            upgrade.set_confirmed(self.is_confirmed)

            Command.execute_cmd(upgrade, call_trigger=False)

    def get_database_type(self):
        project = Project.get_by_code(self.project_code)
        db_resource = project.get_project_db_resource()
        db = DbContainer.get(db_resource)
        return db.get_database_type()




    def _run_managed_sqlite_method(self, name, method):
        """Offline schema transaction, not an application transaction_log write.

        The seed's transaction_log itself needs upgrading. The managed launcher
        runs this on copies and publishes them only after every method succeeds.
        """
        project = Project.get_by_code(self.project_code)
        db = DbContainer.get(project.get_project_db_resource())
        if db.get_database_type() != 'Sqlite':
            raise RuntimeError('Managed SQLite adapter cannot run on another vendor')
        if db.get_connection() is None:
            db.connect()
        upgrade = BaseUpgrade()
        upgrade.set_project(self.project_code)
        upgrade.set_upgrade_class(self.__class__.__name__)
        upgrade.set_upgrade_method(name)
        upgrade.set_quiet(self.quiet)
        upgrade.set_confirmed(self.is_confirmed)
        upgrade.sqlite_managed = self.sqlite_managed
        try:
            db.get_connection().execute("SAVEPOINT native_managed_method")
            method(upgrade)
            db.commit()
            self.sqlite_managed.setdefault('completed', []).append({
                'project': self.project_code, 'class': self.__class__.__name__, 'method': name})
        except Exception:
            db.rollback()
            raise
        finally:
            db.clear_table_cache()

    def run_sql(self, sql):
        ''' run an sql statement. self is an instance of the dynamically created 
        <project_type>Upgrade class. If SqlException arise, it will record the
        error, and the user is advised to check if the error is a result of syntax 
        error or the upgrade function is doing redundant work'''
        project = Project.get_by_code(self.project_code)
        db_resource = project.get_project_db_resource()
        db = DbContainer.get(db_resource)
        if self.sqlite_managed is not None:
            from tactic.core.sqlite_upgrade import SQLiteUpgrade
            if db.get_database_type() != 'Sqlite':
                raise RuntimeError('Unexpected vendor in managed upgrade')
            if db.get_connection() is None:
                db.connect()
            adapter = SQLiteUpgrade(db.get_connection(),
                aliases=self.sqlite_managed.get('aliases', {}).get(self.project_code, {}),
                journal=self.sqlite_managed.setdefault('statements', []),
                method=self.project_code + '/' + str(self.upgrade_method),
                recovery=bool(self.sqlite_managed.get('repair_from')))
            result = adapter.execute(sql)
            db.clear_table_cache()
            return result
        #if not self.quiet:
        #    print(sql)

        # Warnings from MySQL.
        from warnings import filterwarnings
        #filterwarnings('ignore', ' *could not commit.*')
        filterwarnings('ignore', 'Duplicate index .*')

        try:
            db.do_update(sql, quiet=self.quiet)
        except SqlException as e:
            #print("Error: ", e)
            # TEST for Sqlite
            if str(e).startswith("duplicate column name:"):
                pass


            elif str(e).startswith("table") and str(e).endswith("already exists"):
                pass
            # MySQL
            elif str(e).startswith("Duplicate entry"):
                pass

            elif not self.quiet:
                print("\n")
                print("WARNING: Skipping due to SqlException...")
                print("Message: ", e)
                print
            members = inspect.getmembers(self, predicate=inspect.ismethod)
            key = '%s|%s' %(self.project_code, self.upgrade_class)
            
            Container.append_seq(key, (self.upgrade_method, str(e)))
            """  
            for name, member in members:
                # there should only be 1 upgrade method
                if name.startswith('upgrade_v'):       
                    Container.append_seq(key, (self.upgrade_method, str(e)))
                    break
            """          
            # to prevent sql error affecting query that follows the Upgrade
            #DbContainer.abort_thread_sql()
            DbContainer.release_thread_sql()
        else:
            if self.commit_now:
                db.commit()






