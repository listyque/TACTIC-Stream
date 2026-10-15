# Copyright (c) 2005, Southpaw Technology. See LICENSE.TACTIC.
from pyasm.biz import Project
from pyasm.search import SearchType, DbContainer, AlterTableUndo
from pyasm.common import TacticException
from .command import Command


class ColumnAddCmd(Command):
    def __init__(self, search_type, attr_name, attr_type, nullable=True):
        self.search_type = search_type
        self.attr_name = attr_name
        self.attr_type = attr_type
        self.nullable = nullable
        super(ColumnAddCmd,self).__init__()

    def get_data_type(cls, search_type, attr_type):
        search_type_obj = SearchType.get(search_type)

        db_resource = Project.get_db_resource_by_search_type(search_type)
        sql = DbContainer.get(db_resource)
        impl = sql.get_database_impl()


        # SearchType Manager and Add Widget Column use mixed upper and
        # lowercases for the following attr_type, so fix it at some point
        if not attr_type:
            attr_type = "varchar"

        if attr_type == "integer":
            data_type = impl.get_int() 
        elif attr_type == "float":
            data_type = "float"
        elif attr_type == "boolean":
            data_type = impl.get_boolean()
        elif attr_type == "link":
            data_type = "text"
        elif attr_type.startswith('varchar'):
            data_type = attr_type

        elif attr_type == 'time':
            data_type = impl.get_timestamp()
        elif attr_type in ["Date", "date"]:
            data_type = impl.get_timestamp()
        elif attr_type == "Category":
            data_type = "varchar(256)"
        elif attr_type in ["text", "Text"]:
            data_type = impl.get_text()
        elif attr_type == 'numeric':
            data_type = 'numeric'
        elif attr_type in ["Date Range", 'timestamp']:
            data_type = impl.get_timestamp()
        elif attr_type == "Checkbox":
            data_type = "varchar(256)"
        elif attr_type in ["Foreign Key", "foreign_key"]:
            data_type = "varchar(256)"
        elif attr_type in ["List", "list"]:
            data_type = "varchar(512)"
        elif attr_type == "Name/Code":
            data_type = "varchar(256)"
        elif attr_type == "Number":
            data_type = impl.get_int() 

        elif attr_type in ["currency", "scientific", "percent"]:
            data_type = "float"
        elif attr_type == "timecode":
            data_type = impl.get_int() 

        else:
            #data_type = "varchar(256)"
            data_type = impl.get_varchar()

        return data_type

    get_data_type = classmethod(get_data_type)

    def execute(self):

        search_type_obj = SearchType.get(self.search_type)

        db_resource = Project.get_db_resource_by_search_type(self.search_type)
        sql = DbContainer.get(db_resource)
        impl = sql.get_database_impl()

        data_type = self.get_data_type(self.search_type, self.attr_type)


        # if there is no type, then no column is created for widget_config
        if self.attr_type == "Date Range":
            column1 = "%s_start_date" % self.attr_name
            column2 = "%s_end_date" % self.attr_name
            self._add_column(column1, data_type)
            self._add_column(column2, data_type)
        elif self.attr_type != "":
            self._add_column(self.attr_name, data_type)


        self.add_description("Added attribute '%s' of type '%s'" % (self.attr_name, self.attr_type) )

    def _add_column(self, column, type):
        if not type:
            return
        metadata = SearchType.get(self.search_type)
        sql = DbContainer.get(Project.get_db_resource_by_search_type(self.search_type))
        table = metadata.get_table()
        if column in sql.get_column_info(table):
            raise TacticException('[%s] already existed in this table [%s]' % (column, table))
        if not self.nullable:
            type += ' NOT NULL'
        sql.add_column(table, column, type)
        AlterTableUndo.log_add(sql.get_db_resource(), table, column, type)


class ColumnDropCmd(Command):
    """Original ColumnDropCmd using the native Sql/DDL journal."""
    def __init__(self, search_type, attr_name):
        super().__init__()
        self.search_type = search_type
        self.attr_name = attr_name

    def check(self):
        if self.attr_name not in SearchType.get_columns(self.search_type):
            raise TacticException('[%s] does not exist in this table [%s]' % (self.attr_name, self.search_type))
        return True

    def execute(self):
        self.check()
        metadata = SearchType.get(self.search_type)
        sql = DbContainer.get(Project.get_db_resource_by_search_type(self.search_type))
        table = metadata.get_table()
        # Journal values and the table definition before dropping the column.
        # A database resource preserves the owning project/schema, unlike {project}.
        AlterTableUndo.log_drop(sql.get_db_resource(), table, self.attr_name)
        sql.drop_column(table, self.attr_name)
