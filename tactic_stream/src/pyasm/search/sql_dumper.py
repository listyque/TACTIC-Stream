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

__all__ = ['TableSchemaDumper', 'TableDataDumper']

import datetime
import ast
import io
import re
import sys
from decimal import Decimal
from pathlib import Path

from pyasm.common import TacticException, jsondumps
from pyasm.common.errors import UnsupportedContract


def _open_dump(path):
    """Append UTF-8 while retaining the previous file in the Command journal."""
    from pyasm.search import FileUndo
    FileUndo._check_access()
    path = Path(path)
    # ponytail: append keeps the old payload in memory; stream its journal backup if package sizes require it.
    previous = path.read_bytes() if path.exists() else b''
    if path.exists():
        FileUndo.remove(str(path))
    FileUndo.mkdir(str(path.parent))
    FileUndo.create(str(path), io_action=False)
    output = path.open('xb')
    output.write(previous)
    return io.TextIOWrapper(output, encoding='utf-8', newline='\n')


class TableSchemaDumper(object):

    def __init__(self, search_type, delimiter=None):
        self.search_type = search_type
        self.delimiter = delimiter or "#"
        self.end_delimiter = self.delimiter
        self.ignore_columns = []



    def set_delimiter(self, delimiter, end_delimiter=None):
        self.delimiter = delimiter
        if not end_delimiter:
            self.end_delimiter = self.delimiter
        else:
            self.end_delimiter = end_delimiter


    def set_ignore_columns(self, columns=[]):
        self.ignore_columns = columns



    def dump_to_tactic(self, path=None, mode='sql'):
        from pyasm.search import SearchType, DbContainer
        from pyasm.biz import Project
        if mode not in ('sql', 'sobject'):
            raise ValueError('Unknown table dump mode')
        search_type_obj = SearchType.get(self.search_type)
        table = search_type_obj.get_table()
        resource = Project.get_db_resource_by_search_type(self.search_type)
        sql = DbContainer.get(resource)
        impl = sql.get_database_impl()
        if not impl.table_exists(resource, table):
            return
        info = sql.get_column_info(table)
        if not info:
            return
        constraints = impl.get_constraints(resource, table)
        if 'id' not in info:
            raise UnsupportedContract('Only the original id primary key is migrated')
        for constraint in constraints:
            if constraint['mode'] == 'PRIMARY KEY' and constraint['columns'] != ['id']:
                raise UnsupportedContract('Only the original id primary key is migrated')
            if set(constraint['columns']) & set(self.ignore_columns):
                raise TacticException('Cannot ignore constrained columns')
        if not self.delimiter:
            self.delimiter = self.end_delimiter = '--'
        output = _open_dump(path) if path else sys.stdout
        try:
            output.write(self.delimiter + '\n')
            if mode == 'sobject':
                output.write('table = CreateTable(%r)\n' % self.search_type)
            else:
                output.write('table = CreateTable()\ntable.set_table(%r)\n' % table)
            for column in sorted(info):
                if column in self.ignore_columns:
                    continue
                data = info[column]
                # The original export uses portable serial instead of vendor sequences.
                data_type = 'serial' if column == 'id' else data['data_type'].lower()
                args = [repr(column), repr(data_type)]
                if column == 'id':
                    args.append('primary_key=True')
                else:
                    if data_type in ('varchar', 'char', 'nvarchar'):
                        size = data.get('size') or 256
                        args.append('length=%r' % ('max' if size == -1 else size))
                    if not data['nullable']:
                        args.append('not_null=True')
                output.write('table.add(' + ', '.join(args) + ')\n')
            for constraint in constraints:
                if constraint['mode'] != 'PRIMARY KEY':
                    output.write('table.add_constraint(%r, mode=%r)\n' % (constraint['columns'], constraint['mode']))
            output.write(self.end_delimiter + '\n\n')
        finally:
            if path:
                output.close()


class TableDataDumper(object):
    def __init__(self):
        self.sobjects = None
        self.delimiter = "--"
        self.end_delimiter = self.delimiter

        self.database = None
        self.table = None

        self.no_exception = False

        self.pl_sql_var_out_fp = None
        self.pl_sql_ins_out_fp = None
        self.sql_out_fp = None

        self.include_id = True
        self.search_type = None
        self.ignore_columns = []
        self.replace_dict={}
        self.skip_invalid_column = False

    def set_include_id(self, flag=True):
        self.include_id = flag

    def set_ignore_columns(self, columns=[]):
        self.ignore_columns = columns

    def set_skip_invalid_column(self):
        self.skip_invalid_column = True

    def set_replace_token(self, replace, column, regex=None):
        key = column
        value = [replace, regex]
        self.replace_dict[key] = value

    def set_delimiter(self, delimiter, end_delimiter=None):
        self.delimiter = delimiter
        if not end_delimiter:
            self.end_delimiter = self.delimiter
        else:
            self.end_delimiter = end_delimiter

    def set_info(self, table):
        from pyasm.biz import Project
        project = Project.get()
        self.db_resource = project.get_project_db_resource()

        self.table = table

    def set_search_type(self, search_type):
        self.search_type = search_type

    def set_no_exception(self, flag):
        self.no_exception = flag

    def set_sql_out_fps(self, sql_out_fp, pl_sql_var_out_fp, pl_sql_ins_out_fp):
        self.sql_out_fp = sql_out_fp
        self.pl_sql_var_out_fp = pl_sql_var_out_fp
        self.pl_sql_ins_out_fp = pl_sql_ins_out_fp

    def set_sobjects(self, sobjects):
        from pyasm.biz import Project
        from pyasm.search import SearchType
        self.sobjects = list(sobjects)
        if not self.sobjects:
            return
        first = self.sobjects[0]
        self.search_type = first.get_search_type()
        self.search_type_obj = SearchType.get(self.search_type)
        self.table = self.search_type_obj.get_table()
        # System objects use the system DB, not their project_code field.
        self.db_resource = Project.get_db_resource_by_search_type(self.search_type)

    def dump_tactic_inserts(self, path, mode='sql', relative_dir_column=None):
        if mode != 'sobject':
            raise UnsupportedContract('Raw SQL dump statements are not migrated')
        from pyasm.search import Search
        if self.sobjects is None:
            if not self.search_type:
                raise TacticException('A search type is required for data export')
            search = Search(self.search_type)
            search.set_show_retired(True)
            self.set_sobjects(search.get_sobjects())
        output = None
        try:
            if not relative_dir_column:
                output = _open_dump(path) if path else sys.stdout
            for sobject in self.sobjects:
                if relative_dir_column:
                    if not path:
                        output = sys.stdout
                    else:
                        directory = Path(path).resolve()
                        name = str(sobject.get_value(relative_dir_column)).replace('.', '/') + '.spt'
                        target = directory / name
                        if '\\' in name or ':' in name or not target.resolve().is_relative_to(directory):
                            raise TacticException('SPT relative path escapes its directory')
                        output = _open_dump(target)
                output.write(self.delimiter + '\n')
                output.write('insert = SearchType.create(%r)\n' % sobject.get_base_search_type())
                if self.skip_invalid_column:
                    output.write('insert.skip_invalid_column()\n')
                data = sobject.get_data()
                for name in sorted(data):
                    if name in self.ignore_columns or name == '_tmp_spt_rownum' or name == 'id' and not self.include_id:
                        continue
                    value = data[name]
                    if value is None:
                        output.write('insert.set_value(%r, None, allow_none=True)\n' % name)
                        continue
                    if name in self.replace_dict:
                        replacement, regex = self.replace_dict[name]
                        value = re.sub(regex, replacement, value) if regex else replacement
                    if isinstance(value, (dict, list)):
                        value = jsondumps(value)
                    elif isinstance(value, (datetime.datetime, datetime.date, datetime.time, Decimal)):
                        value = str(value)
                    elif not isinstance(value, (str, int, float, bool, bytes)):
                        raise TacticException('Unsupported SPT value: ' + type(value).__name__)
                    # repr preserves quotes, slashes and newlines without changing script bodies.
                    literal = repr(value)
                    ast_value = ast.literal_eval(literal)
                    if ast_value != value:
                        raise TacticException('Invalid SPT literal')
                    output.write('insert.set_value(%r, %s)\n' % (name, literal))
                output.write(self.end_delimiter + '\n\n')
                if relative_dir_column and path:
                    output.close()
                    output = None
        finally:
            if output is not None and output is not sys.stdout:
                output.close()

