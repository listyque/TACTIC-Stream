###########################################################
#
# Copyright (c) 2009, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#
__all__ = ["DeleteToolWdg", "DeleteCmd", "DeleteSearchTypeToolWdg", 'DeleteSearchTypeCmd', "DeleteProjectToolWdg", "DeleteProjectCmd"]
__all__ = ['DeleteCmd', 'DeleteSearchTypeCmd']

import os
from pyasm.common import Environment
from pyasm.common.errors import UnsupportedContract
from pyasm.biz import Schema, Snapshot, FileGroup, FileRange
from pyasm.command import Command
from pyasm.search import Search, SearchType, FileUndo
from pyasm.security import Sudo

class DeleteSearchTypeCmd(Command):
    """Native table/registration deletion; DropTable owns the undo snapshot."""

    def check(self):
        from pyasm.security.security import _require_admin
        from pyasm.biz import Project
        from pyasm.common import TacticException
        _require_admin()
        self.search_type = self.kwargs['search_type']
        self.values = self.kwargs.get('values')
        self.search_type_obj = SearchType.get(self.search_type)
        self.db_resource = SearchType.get_db_resource_by_search_type(self.search_type)
        self.database = self.db_resource.get_database()
        from pyasm.search import DbContainer
        if self.db_resource.get_key() not in (
                Project.get().get_project_db_resource().get_key(), DbContainer.get('sthpw').get_db_resource().get_key()):
            raise TacticException('You are not allowed to delete the sType [%s] from another project [%s].'
                                  % (self.search_type, self.database))
        return True

    def execute(self):
        from pyasm.search import DbContainer, DropTable
        # API/Batch does not invoke Command.check(), so validate here as well.
        self.check()
        sql = DbContainer.get(self.db_resource)
        sql.check_schema_write()
        sql.get_database_impl().lock_table_for_drop(sql, self.search_type_obj.get_table())
        query = Search(self.search_type)
        query.set_show_retired(True)
        for sobject in query.get_sobjects():
            DeleteCmd(sobject=sobject, values=self.values).execute()
        # Do not swallow SQL errors: the enclosing native command must roll back.
        DropTable(self.search_type).commit()
        if self.search_type_obj.get_value('database') != '{project}':
            self.search_type_obj.delete()

class DeleteCmd(Command):

    def requires_key(self):
        return True

    def is_undoable(cls):
        return True
    is_undoable = classmethod(is_undoable)

    def execute(self):
        FileUndo._check_access()

        # if a single sobject is passed in
        sobject = self.kwargs.get("sobject")
        if not sobject:
            search_key = self.kwargs.get("search_key")
            sobject = Search.get_by_search_key(search_key)

        if sobject:
            sobjects = [sobject]
        else:
            search_keys = self.kwargs.get("search_keys")
            try:
                sudo = Sudo()
                sobjects = [Search.get_by_search_key(key) for key in search_keys]
            finally:
                sudo.exit()

        if not sobjects:
            return


        # find all the relationships
        self.schema = Schema.get()

        for sobject in sobjects:
            self.delete_sobject(sobject)




    def delete_sobject(self, sobject):

        search_type = sobject.get_base_search_type()

        # this is used by API method delete_sobject
        auto_discover = self.kwargs.get("auto_discover")

        values = self.kwargs.get("values")
        if values:
            related_types = values.get("related_types")
        elif auto_discover:
            related_types = SearchType.get_related_types(search_type, direction="children")
        else:
            related_types = None

        return self.do_delete(sobject, related_types)



    def do_delete(self, sobject, related_types=None):
        FileUndo._check_access()
        if sobject.get_base_search_type() == 'sthpw/file':
            snapshot = Snapshot.get_by_code(sobject.get_value('snapshot_code'))
            if snapshot is None:
                raise TacticException('Snapshot owner is no longer available')
            snapshot.remove_file(sobject.get_type(), file_code=sobject.get_code())
            return
        base = sobject.get_base_search_type()
        if base.startswith(('sthpw/', 'config/')) and base not in sobject.SECURITY_TYPES + sobject.BUSINESS_TYPES:
            raise UnsupportedContract('This dependency deletion requires its domain write migration')

        search_type = sobject.get_base_search_type()

        # always delete notes and task and snapshot
        if not related_types:
            related_types = ['sthpw/note', 'sthpw/task', 'sthpw/snapshot']
        #related_types = self.schema.get_related_search_types(search_type)

        if related_types:
            for related_type in related_types:
                if not related_type or related_type == search_type:
                    continue

                # snapshots take care of sthpw/file in the proper manner, so
                # skip them here
                if related_type == 'sthpw/file':
                    continue

                related_sobjects = sobject.get_related_sobjects(related_type, show_retired=True)
                for related_sobject in related_sobjects:
                    if related_type == 'sthpw/snapshot':
                        self.delete_snapshot(related_sobject)
                    else:
                        related_sobject.delete()
                        #self.do_delete(related_sobject)


        # implicitly remove "directory" files associated with the sobject
        search = Search("sthpw/file")
        search.add_op("begin")
        search.add_filter("file_name", "")
        search.add_null_filter("file_name")
        search.add_op("or")
        search.add_parent_filter(sobject)
        file_objects = search.get_sobjects()

        #if file_objects:
        #    print("Removing [%s] file objects" % len(file_objects))

        for file_object in file_objects:
            base_dir = Environment.get_asset_dir(file_object=file_object)
            relative_dir = file_object.get("relative_dir")
            lib_dir = "%s/%s" % (base_dir, relative_dir)
            FileUndo.rmdir(lib_dir)
            file_object.delete()


        # finally delete the sobject
        print("Deleting: ", sobject.get_search_key())
        if search_type == 'sthpw/snapshot':
            self.delete_snapshot(sobject)
        else:
            sobject.delete()




    def delete_snapshot(self, snapshot):

        FileUndo._check_access()
        snapshot._lock_versions()
        # Only owned File rows are deleted; direct XML references may be shared.
        files = snapshot.get_related_sobjects("sthpw/file", show_retired=True)
        paths = []
        from tactic_stream.server.file_presentation import metadata_paths
        for file in files:
            path = os.path.join(file.get_lib_dir(snapshot=snapshot), file.get_file_name())
            paths.extend(FileGroup.expand_paths(path, FileRange.get(file.get_file_range())) if file.get_value('base_type') == 'sequence' else [str(member) for member in metadata_paths(file)])
        for file in files:
            print("Deleting file: ", file.get_search_key())
            file.delete()

        # remove the files from the repo
        for file_path in paths:
            print("Removing path: ", file_path)
            FileUndo.remove(file_path)
            if snapshot.get_version() in (-1, 0):
                FileUndo.remove(os.path.join(os.path.dirname(file_path), '.' + os.path.basename(file_path) + '.link'))


        # get info before deleting
        search_type = snapshot.get("search_type")
        search_code = snapshot.get("search_code")
        context = snapshot.get_value("context")
        version = snapshot.get_value("version")

        print("Deleting snapshot: ", snapshot.get_search_key())
        snapshot.delete()


        # Alias deletion must not promote another alias or recurse back to itself.
        if version in (-1, 0):
            return
        identity = search_code or snapshot.get_value('search_id')
        for mode, flag in (('latest', 'is_latest'), ('current', 'is_current')):
            search = Search('sthpw/snapshot')
            search.add_filter('search_type', search_type)
            search.add_filter('search_code' if search_code else 'search_id', identity)
            search.add_filter('context', context)
            search.add_filter('level_type', snapshot.get_value('level_type') or None)
            search.add_filter('level_id', snapshot.get_value('level_id') or None)
            search.add_filter('version', 0, op='>')
            search.add_filter(flag, True)
            target = search.get_sobject()
            if target:
                target.update_versionless(mode)
            else:
                alias = Snapshot._get_versionless(search_type, identity, context, mode=mode, create=False,
                    level_type=snapshot.get_value('level_type') or None,
                    level_id=snapshot.get_value('level_id') or None)
                if alias:
                    self.delete_snapshot(alias)
