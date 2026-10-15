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
# Description: Custom properties are a list of properties added to sobjects
#   that are not part of the standard templates.

__all__ = ["CustomProperty"]


from pyasm.search import SObject, SearchType, AlterTableUndo, DbContainer


class CustomProperty(SObject):

    SEARCH_TYPE = "prod/custom_property"
    
    def delete(self, log=False):
        if log:
            # Authorize before changing the target schema, using its actual resource.
            self._check_business_write()
            from pyasm.biz import Project
            search_type = self.get_value("search_type")
            table = SearchType.get(search_type).get_table()
            resource = Project.get_db_resource_by_search_type(search_type)
            sql = DbContainer.get(resource)
            sql.check_schema_write()
            column = self.get_value("name")
            AlterTableUndo.log_drop(resource, table, column)
            sql.drop_column(table, column)
        return super(CustomProperty, self).delete(log)
