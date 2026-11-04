# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION. This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
# See LICENSE.TACTIC for the distribution license.
"""Native Sql/DbResource/DbContainer, SQLite and PostgreSQL resources.

Adapted from pyasm/search/sql.py; see LICENSE.TACTIC/source_manifest.json.
System identity checks use the configured database without recursive Sql access.
Raw writes require an administrator. Ordinary PostgreSQL account mutations use
bound native DML after the SObject/security checks, never caller-supplied SQL.
"""
from contextlib import closing, contextmanager
from hashlib import sha256
import datetime
import re
from dateutil import parser

import sqlite3
import uuid

from pyasm.common.common import Base, Container, TacticException, jsondumps, jsonloads
from pyasm.common import SPTDate
from pyasm.search.database_impl import DatabaseImpl
from pyasm.common.errors import UnsupportedContract
from pyasm.search.storage import identifier


class SqlException(TacticException):
    pass


class DatabaseException(TacticException):
    pass


class Select(object):
    """A class to non-linearly build up an sql select statement"""

    def __init__(self):
        self.tables = []
        self.id_col = 'id'
        self.columns = []
        self.as_columns = []
        self.column_tables = []
        self.wheres = []
        self.filters = {}
        self.raw_filters = []
        self.filter_mode = 'AND'
        self.group_bys = []
        self.havings = []
        self.order_bys = []
        self.order_by_columns = []
        self.limit = None
        self.offset = 0
        self.distinct = False
        self.distinct_col = None
        self.joins = []
        self.join_tables = set()
        self.sql = None
        self.database = None
        self.db_resource = None
        self.column_types = {}
        self.impl = DatabaseImpl.get()
        self.statement = None
        self._statement = None
        self.schema = ''
        self.quoted_mode = None

    def copy(self):
        from copy import deepcopy
        if getattr(self, '_search_owned', False):
            return self._search_owned.copy().select
        select = Select()
        select.__dict__.update({key: value if key in ('sql', 'db_resource', 'impl') else deepcopy(value) for key, value in self.__dict__.items() if key != 'cursor'})
        return select

    def dumps(self):
        owner = getattr(self, '_search_owned', None)
        if owner:
            owner._statement()
        data = {name: value for name, value in self.__dict__.items() if name not in ('sql', 'db_resource', 'impl', 'cursor', '_search_owned')}
        data['join_tables'] = list(self.join_tables)
        data['set_statement'] = data.pop('_statement')
        if owner:
            values = iter(owner.parameters)
            wheres = []
            try:
                for where in self.wheres:
                    parts = Sql._parameter_parts(where, owner._placeholder())
                    rendered = []
                    for part in parts[:-1]:
                        rendered.append(part + Sql.quote(next(values)))
                    wheres.append(''.join(rendered) + parts[-1])
            except StopIteration:
                raise SqlException('Search parameter count does not match its filters') from None
            if next(values, values) is not values:
                raise SqlException('Search parameter count does not match its filters')
            if owner.retired_filter:
                column = owner._column('s_status')
                wheres.append("(%s IS NULL OR %s != 'retired')" % (column, column))
            if owner.null_filter:
                wheres.append('1 = 0')
            data['wheres'] = wheres
        return jsondumps(data)

    def loads(self, data):
        data = jsonloads(data)
        owner = getattr(self, '_search_owned', None)
        if owner:
            from tactic.command.python_cmd import check_script_execution
            from pyasm.search import Search
            check_script_execution(require_transaction=False)
            if not isinstance(data, dict):
                raise ValueError('Select state must be a JSON object')
            candidate = Select()
            candidate.loads(jsondumps(data))
            if candidate.tables != [owner.table] or candidate.filters or candidate._statement not in (None, ''):
                raise UnsupportedContract('Replacing Search tables or loading raw Select filters is not migrated')
            if candidate.database not in (None, owner.get_database()):
                raise UnsupportedContract('Serialized Select cannot replace the Search database')
            if candidate.schema not in (None, '', owner.db_resource.get_schema() or 'public'):
                raise UnsupportedContract('Serialized Select cannot replace the Search schema')
            for name in ('columns', 'column_tables', 'as_columns', 'wheres', 'joins', 'group_bys', 'havings', 'order_bys', 'order_by_columns'):
                items = getattr(candidate, name)
                optional = name in ('column_tables', 'as_columns')
                if not isinstance(items, list) or any(not isinstance(item, str) and not (optional and item is None) for item in items):
                    raise ValueError('Invalid Select ' + name)
            if 'as_columns' not in data:
                candidate.as_columns = [None] * len(candidate.columns)
            if len(candidate.columns) != len(candidate.column_tables) or len(candidate.columns) != len(candidate.as_columns):
                raise ValueError('Select projection fields have different lengths')
            if (candidate.limit is not None and (type(candidate.limit) is not int or candidate.limit < 0)
                    or type(candidate.offset) is not int or candidate.offset < 0):
                raise ValueError('Invalid Select pagination')
            if candidate.filter_mode not in ('AND', 'OR') or candidate.quoted_mode not in (None, 'none'):
                raise ValueError('Invalid Select filter or quote mode')
            if type(candidate.distinct) is not bool or not isinstance(candidate.id_col, str):
                raise ValueError('Invalid Select flags')
            if not isinstance(candidate.raw_filters, list):
                raise ValueError('Invalid Select raw filter metadata')
            fresh = Search(owner.search_type, project_code=owner.project_code)
            if fresh.store is not owner.store or not owner._same_database(fresh.db_resource):
                raise UnsupportedContract('Serialized Select requires the current Search resource')
            joined = {owner.table: fresh.columns}
            for join in candidate.joins:
                match = re.fullmatch(r'(?:LEFT OUTER|INNER|RIGHT OUTER) JOIN ((?:"[A-Za-z_][\w]*"\.){0,2})"([A-Za-z_][\w]*)"(?: AS "([A-Za-z_][\w]*)")? ON .+', join)
                if not match:
                    raise UnsupportedContract('Serialized Search Select join syntax is not migrated')
                qualifiers = re.findall(r'"([^"]+)"', match[1])
                if qualifiers and qualifiers[-1] != (owner.db_resource.get_schema() or 'public'):
                    raise UnsupportedContract('Serialized Select cannot join another schema')
                if len(qualifiers) == 2 and qualifiers[0] != owner.get_database():
                    raise UnsupportedContract('Serialized Select cannot join another database')
                joined[match[3] or match[2]] = owner.store.columns(owner.db_resource, match[2])
            for column, table, alias in zip(candidate.columns, candidate.column_tables, candidate.as_columns):
                if table is not None and candidate.quoted_mode != 'none':
                    if table not in joined or column != '*' and column not in joined[table]:
                        raise ValueError('Serialized Select projection refers to an unknown column')
                if alias:
                    identifier(alias)
            for where in candidate.wheres:
                if len(Sql._parameter_parts(where, owner._placeholder())) != 1:
                    raise ValueError('Serialized Select contains an unbound parameter')
            candidate.join_tables = set(joined) - {owner.table}
            for name in ('sql', 'db_resource', 'impl', '_search_owned'):
                setattr(candidate, name, getattr(self, name))
            self.__dict__.update(candidate.__dict__)
            owner.filters, owner.parameters = self.wheres, []
            owner.joins, owner.join_columns = self.joins, joined
            owner.join_sources = self.join_tables.copy()
            owner.order_bys, owner.selected_columns = self.order_bys, self.columns
            owner.order_columns = set(self.order_by_columns)
            owner.limit, owner.offset = self.limit, self.offset
            owner.distinct = self.distinct
            owner.null_filter = owner.null_filter or fresh.null_filter
            owner.raw_where = True
            owner.custom_filter = owner.security_filter = owner.is_search_done = False
            owner.sobjects = []
            return
        self._statement = data.pop('set_statement', None)
        for name in ('tables', 'id_col', 'columns', 'as_columns', 'column_tables', 'wheres', 'filters', 'raw_filters', 'filter_mode', 'group_bys', 'havings', 'order_bys', 'order_by_columns', 'limit', 'offset', 'distinct', 'distinct_col', 'joins', 'schema', 'database', 'quoted_mode'):
            if name in data:
                setattr(self, name, data[name])
        self.join_tables = set(data.get('join_tables', []))

    def execute(self, sql=None):
        sql = sql or self.sql
        if sql is None and getattr(self, '_search_owned', False):
            sql = self._search_owned.get_sql()
        if sql is None:
            raise SqlException('No connector found to execute query')
        if getattr(self, '_search_owned', False) and not self._search_owned._same_database(sql.get_db_resource()):
            raise UnsupportedContract('Execute a Search Select on its own database resource')
        return sql.do_query(self.get_statement())

    def execute_count(self, sql=None):
        sql = sql or self.sql
        if sql is None and getattr(self, '_search_owned', False):
            sql = self._search_owned.get_sql()
        if sql is None:
            raise SqlException('No connector found to execute query')
        if getattr(self, '_search_owned', False) and not self._search_owned._same_database(sql.get_db_resource()):
            raise UnsupportedContract('Execute a Search Select on its own database resource')
        return sql.get_int(self.get_count())

    def __str__(self):
        return self.get_statement()

    def set_database(self, database):
        assert database == 'sthpw' or not isinstance(database, str)
        if isinstance(database, str):
            self.sql = DbContainer.get(database)
            self.db_resource = DbResource.get_default(database)
        elif DbResource.is_instance(database):
            self.sql = DbContainer.get(database)
            self.db_resource = database
            database = database.get_database()
        elif isinstance(database, Sql):
            self.sql = database
            database = self.sql.get_database_name()
            self.db_resource = self.sql.get_db_resource()
        else:
            self.sql = database
            database = self.sql.get_database_name()
            self.db_resource = DbResource.get_default(database)
        self.database = database
        self.impl = self.sql.get_database_impl()
        database_type = self.impl.get_database_type()
        if database_type == 'PostgreSQL':
            self.schema = self.db_resource.get_schema() or 'public'
        elif database_type == 'SQLServer':
            self.schema = 'dbo'
        elif database_type == 'Sqlite':
            self.database = None

    def set_statement(self, statement):
        """special function which allows you to put in an arbitrary sql
        statement and dynamically add operations to it.  There are limitations
        to this"""
        self.tables.append('( %s )' % statement)
        self._statement = statement

    def add_table(self, table):
        if table == '':
            return
        self.tables.append(table)

    def get_tables(self):
        return self.tables

    def get_table(self):
        return self.tables[0]

    def set_id_col(self, id_col):
        self.id_col = id_col

    def add_join(self, table1, table2=None, column=None, column2=None, join='LEFT OUTER', database=None, database2=None):
        """
        SELECT *
        FROM "job"

        RIGHT OUTER JOIN "request"
        ON "request
        """
        join = join.upper()
        assert join in ['LEFT OUTER', 'INNER', 'RIGHT OUTER']
        owner = getattr(self, '_search_owned', None)
        if owner:
            from tactic.command.python_cmd import check_script_execution
            check_script_execution(require_transaction=False)
            if database or database2:
                raise UnsupportedContract('Cross-resource direct Search Select joins are not migrated')
        if not table2:
            table2 = table1
            table1 = self.tables[0]
        if table2 in self.join_tables:
            return
        if owner:
            owner.join_columns[table2] = owner.store.columns(owner.db_resource, table2)
            owner.raw_where = True
        self.join_tables.add(table2)
        if column and column2:
            column1 = column
        elif not column:
            column1 = '%s_id' % table2
            columns = self.impl.get_column_info(self.db_resource, table1).keys()
            if column1 not in columns:
                column1 = 'id'
                column2 = '%s_id' % table1
            else:
                column2 = 'id'
        else:
            column1 = column
            column2 = 'id'
        if not database:
            database1 = self.database
        else:
            database1 = database
        parts = []
        if database1:
            parts.append('"%s"' % database1)
        if self.schema:
            parts.append('"%s"' % self.schema)
        prefix1 = '.'.join(parts)
        if prefix1:
            prefix1 = '%s.' % prefix1
        if not database2:
            database2 = self.database
        parts = []
        if database2:
            parts.append('"%s"' % database2)
        if self.schema:
            parts.append('"%s"' % self.schema)
        prefix2 = '.'.join(parts)
        if prefix2:
            prefix2 = '%s.' % prefix2
        expr = '%s JOIN %s"%s" ON "%s"."%s" = "%s"."%s"' % (join, prefix2, table2, table1, column1, table2, column2)
        if self.impl.get_database_type() == 'SQLServer':
            expr = '%s JOIN %s"%s" ON "%s"."%s" = %s"%s"."%s"' % (join, prefix2, table2, table1, column1, prefix2, table2, column2)
        self.joins.append(expr)

    def set_quoted_mode(self, mode):
        self.quoted_mode = mode

    def add_column(self, column, distinct=False, table=None, as_column=None, quoted=True):
        if (column == '' or column in self.columns) and column != '*':
            return
        self.columns.append(column)
        self.as_columns.append(as_column)
        if not quoted:
            self.column_tables.append(None)
        elif table:
            self.column_tables.append(table)
        else:
            self.column_tables.append(self.tables[0])
        if distinct:
            self.distinct_col = column
        self.distinct = distinct

    def set_distinct_col(self, column):
        self.distinct = True
        self.distinct_col = column

    def get_columns(self):
        columns = []
        for column, as_column in zip(self.columns, self.as_columns):
            if as_column:
                columns.append(as_column)
            else:
                columns.append(column)
        return columns

    def set_filter_mode(self, mode):
        assert mode in ['and', 'or']
        self.filter_mode = mode.upper()

    def add_where(self, where):
        if getattr(self, '_search_owned', False):
            return self._search_owned.add_where(where)
        self.wheres.append(where)

    def add_op(self, op, idx=None):
        assert op in ['and', 'or', 'begin']
        self.raw_filters.append({'op': op})
        if idx == None:
            self.wheres.append(op)
        else:
            self.wheres.insert(idx, op)

    def get_wheres(self):
        return self.wheres

    def remove_where(self, where):
        if getattr(self, '_search_owned', False) and where in self.wheres:
            owner = self._search_owned
            marker = owner._placeholder()
            index = self.wheres.index(where)
            start = sum(len(Sql._parameter_parts(item, marker)) - 1 for item in self.wheres[:index])
            del owner.parameters[start:start + len(Sql._parameter_parts(where, marker)) - 1]
        try:
            self.wheres.remove(where)
        except:
            pass

    def _convert_to_database_boolean(self, value):
        if not self.impl.get_database_type() == 'SQLServer':
            return value
        if value == 'true' or value == 'TRUE':
            return '1'
        elif value == 'false' or value == 'FALSE':
            return '0'
        return value

    def add_filter(self, column, value, column_type='', op='=', quoted=None, table=''):
        if (getattr(self, '_search_owned', False) and self.quoted_mode != 'none'
                and quoted is not False and value != '__ALL__'):
            return self._search_owned.add_filter(column, value, op=op, quoted=quoted, table=table)
        assert self.tables
        if not self.db_resource:
            column_type = 'varchar'
        else:
            column_types = self.impl.get_column_types(self.db_resource, self.tables[0])
            column_type = column_types.get(column)
        if column_type in ['timestamp', 'datetime', 'datetime2']:
            if isinstance(value, str):
                if value.lower() == 'now':
                    info = self.impl.process_value(column, value, column_type)
                    if info:
                        value = info.get('value')
                        quoted = info.get('quoted')
                else:
                    try:
                        value = parser.parse(value)
                    except ValueError:
                        pass
            if isinstance(value, datetime.datetime):
                value = SPTDate.convert_to_local(value)
                info = self.impl.process_value(column, value, column_type)
                if info:
                    value = info.get('value')
                    quoted = info.get('quoted')
        self.raw_filters.append({'column': column, 'value': value, 'column_type': column_type, 'op': op, 'quoted': quoted, 'table': table})
        if self.quoted_mode == 'none':
            where = "%s %s '%s'" % (column, op, value)
            self.add_where(where)
            return
        subcolumn = None
        if column.find('->>') != -1:
            parts = column.split('->>')
            column = parts[0]
            subcolumn = parts[1]
        elif column.find('->') != -1:
            parts = column.split('->')
            column = parts[0]
            subcolumn = parts[1]
        if not table:
            table = self.tables[0]
        if column == 'id' and value == None:
            where = '"%s"."%s" is NULL' % (table, column)
            self.add_where(where)
            return
        if value == None:
            where = '"%s"."%s" is NULL' % (table, column)
            self.add_where(where)
            return
        if quoted == 'column':
            value = '"%s"' % value
            quoted = False
        if isinstance(value, list) and len(value) == 0:
            where = '"%s" is NULL' % column
            self.add_where(where)
            return
        if quoted == None:
            quoted = True
            info = self.impl.process_value(column, value, column_type)
            if info:
                value = info.get('value')
                value = self._convert_to_database_boolean(value)
                quoted = info.get('quoted')
        if op not in ['in', 'not in'] and isinstance(value, (list, tuple)):
            value = value[0]
        if quoted:
            value = Sql.quote(value)
        if subcolumn:
            if value == 'NULL':
                json_op = '->'
            else:
                json_op = '->>'
        if table:
            if subcolumn:
                where = '"%s"."%s"%s\'%s\' %s %s' % (table, column, json_op, subcolumn, op, value)
            else:
                where = '"%s"."%s" %s %s' % (table, column, op, value)
        elif subcolumn:
            where = '"%s"%s\'%s\' %s %s' % (column, json_op, subcolumn, op, value)
        else:
            where = '"%s" %s %s' % (column, op, value)
        self.add_where(where)

    def add_filters(self, column, values, table='', op='in'):
        if getattr(self, '_search_owned', False):
            return self._search_owned.add_filters(column, values, table=table, op=op)
        quoted = False
        column_type = ''
        self.raw_filters.append({'column': column, 'value': values, 'column_type': column_type, 'op': op, 'quoted': quoted, 'table': table})
        assert op in ['in', 'not in', '@@', '@>']
        if op == '@@':
            self.add_op('begin')
            for value in values:
                self.add_filter(column, value, table, op)
            self.add_op('or')
            return
        if not table:
            table = self.tables[0]
        filter = ''
        if not values or values == ['']:
            if table:
                where = '"%s"."%s" is NULL' % (table, self.id_col)
            else:
                where = '%s is NULL' % self.id_col
        else:
            list = [Sql.quote(value) for value in values]
            if table:
                where = '"%s"."%s" %s (%s)' % (table, column, op, ', '.join(list))
            else:
                where = '"%s" %s (%s)' % (column, op, ', '.join(list))
        self.add_where(where)

    def add_group_aggregate_filter(self, group_cols, column='id', aggregate='max'):
        """This does a co-related subselect which finds the result of an
        aggregate function over a list of grouped columns

        Searching for the max version for each context of a snapshot.
        This is called by:

        select.add_group_aggregate_filter(['search_type','search_id','context'], "version")

        This producess the following sql:

        select * from snapshot where version = (select max(version) from snapshot as f where f.search_type = snapshot.search_type and f.search_id = snapshot.search_id and f.context = snapshot.context) order by search_type, search_id;

        Reference:
        http://www.xaprb.com/blog/2006/12/07/how-to-select-the-firstleastmax-row-per-group-in-sql/

        """
        if not group_cols:
            return
        if isinstance(group_cols, str):
            group_cols = [group_cols]
        table = self.get_table()
        subselect = []
        subselect.append('SELECT')
        subselect.append('%s("%s")' % (aggregate, column))
        subselect.append('FROM')
        if self.impl.get_database_type() == 'SQLServer':
            subselect.append('[%s] as xxx' % table)
        else:
            subselect.append('"%s" as xxx' % table)
        subselect.append('WHERE')
        wheres = []
        for group_col in group_cols:
            if self.impl.get_database_type() == 'SQLServer':
                wheres.append('xxx."%s" = [%s].[%s]' % (group_col, table, group_col))
            else:
                wheres.append('xxx."%s" = "%s"."%s"' % (group_col, table, group_col))
        wheres = ' AND '.join(wheres)
        subselect.append(wheres)
        statement = ' '.join(subselect)
        if self.impl.get_database_type() == 'SQLServer':
            self.add_where('[%s].[%s] = (%s)' % (table, column, statement))
        else:
            self.add_where('"%s"."%s" = (%s)' % (table, column, statement))

    def add_text_search_filter(self, column, keywords, table=None, op='&'):
        """This will do full text searching on any column.  It is pretty
        brute force as it will convert each row to a ts_vector.
        """
        if not table:
            table = self.tables[0]
        column_types = self.impl.get_column_types(self.db_resource, table)
        column_type = column_types.get(column)
        where = self.impl.get_text_search_filter(column, keywords, column_type, table=table, op=op)
        self.add_where(where)

    def add_select_filter(self, column, select, op='in', table=''):
        """combines results of one search filter with another search filter
        as a subselect

        example:

        SELECT * FROM "request" WHERE "id" in ( SELECT "request_id" FROM "job" WHERE "code" = '123MMS' )
        """
        assert op in ['in', 'not in']
        statement = select.get_statement()
        self.add_filter(column, '( %s )' % statement, op=op, quoted=False, table=table)

    def add_group_by(self, group_by):
        if group_by == '':
            return
        self.group_bys.append(group_by)

    def add_having(self, having):
        if having == '':
            return
        self.havings.append(having)

    def add_order_by(self, order_by, direction='', table=''):
        if order_by == '':
            return
        if order_by.find('->') != -1:
            parts = order_by.split(' ')
            parts2 = parts[0].split('->')
            parts2[1] = parts2[1].strip("'")
            order_by = '"%s"->\'%s\'' % (parts2[0], parts2[1])
        elif table:
            order_by = '"%s"."%s"' % (table, order_by)
        if direction and (not order_by.endswith(' desc')) and (not order_by.endswith(' asc')):
            if order_by not in self.order_by_columns:
                self.order_by_columns.append(order_by)
            else:
                return
            order_by = '%s %s' % (order_by, direction)
        elif order_by.endswith(' desc') or order_by.endswith(' asc'):
            tmps = order_by.split(' ')
            if tmps[0] not in self.order_by_columns:
                self.order_by_columns.append(tmps[0])
            else:
                return
        elif order_by not in self.order_by_columns:
            self.order_by_columns.append(order_by)
        else:
            return
        if order_by not in self.order_bys:
            self.order_bys.append(order_by)

    def add_enum_order_by(self, column, values, table=''):
        """orders by a list of values.
        takes a list of values and creates a case statement out of it"""
        if not values:
            return
        expr = []
        if table:
            expr.append('( CASE "%s"."%s"' % (table, column))
        else:
            expr.append('( CASE "%s"' % column)
        count = 1
        for value in values:
            if isinstance(value, str):
                value = Sql.quote(value)
            expr.append('WHEN %s THEN %d ' % (value, count))
            count += 1
        expr.append('ELSE %d END )' % count)
        self.add_order_by('\n'.join(expr))

    def add_limit(self, limit):
        """deprecated: use set_limit"""
        self.limit = limit

    def set_limit(self, limit):
        self.limit = limit

    def set_offset(self, offset):
        self.offset = offset

    def get_statement(self, mode='normal'):
        if getattr(self, '_search_owned', False):
            owner = self._search_owned
            statement, values = owner._statement(default_order=mode != 'count', count=mode == 'count')
            marker = owner._placeholder()
            parts = Sql._parameter_parts(statement, marker)
            if len(parts) != len(values) + 1:
                raise SqlException('Search parameter count does not match its filters')
            return ''.join(part + Sql.quote(value) for part, value in zip(parts, values)) + parts[-1]
        if self._statement:
            return self._statement
        if not self.tables:
            raise SqlException("No tables defined")
        if self.impl:
            database_type = self.impl.get_database_type()
        else:
            database_type = Sql.get_default_database_type()
        regex_asc = re.compile(' asc$', re.I)
        regex_desc = re.compile(' desc$', re.I)
        statement = []
        statement.append('SELECT')
        is_oracle = False
        if database_type == 'Oracle' and self.tables[0] not in ['USER_OBJECTS', 'ALL_TABLES']:
            is_oracle = True
        if mode == 'count':
            if database_type == 'PostgreSQL' and self.distinct_col:
                statement.append('count(DISTINCT %s)' % self.distinct_col)
            else:
                statement.append('count(*)')
        elif mode == 'normal':
            if database_type == 'SQLServer' and self.limit != None:
                total = int(self.limit) + self.offset
                statement.append('TOP %s ' % total)
            if not self.columns:
                if is_oracle:
                    expr = '%s."%s".*' % (self.database, self.tables[0])
                    statement.append(expr)
                elif database_type == 'PostgreSQL' and self.distinct_col:
                    statement.append('DISTINCT ON(%s) *' % self.distinct_col)
                else:
                    column_parts = []
                    if self.database:
                        column_parts.append('"%s"' % self.database)
                    if self.schema:
                        column_parts.append('"%s"' % self.schema)
                    column_parts.append('"%s"' % self.tables[0])
                    column_parts.append('*')
                    expr = '.'.join(column_parts)
                    statement.append(expr)
            else:
                quoted_cols = []
                for i, column in enumerate(self.columns):
                    if column == self.distinct_col:
                        parts = []
                        if self.database:
                            parts.append('"%s"' % self.database)
                        if self.schema:
                            parts.append('"%s"' % self.schema)
                        parts.append('"%s"' % self.column_tables[i])
                        prefix = '.'.join(parts)
                        quoted_col = 'distinct %s."%s"' % (prefix, column)
                    elif self.quoted_mode == 'none':
                        quoted_col = column
                    else:
                        parts = []
                        column_table = self.column_tables[i]
                        if column_table:
                            if self.database:
                                parts.append('"%s"' % self.database)
                            if self.schema:
                                parts.append('"%s"' % self.schema)
                            parts.append('"%s"' % self.column_tables[i])
                            if column == '*':
                                parts.append(column)
                            else:
                                parts.append('"%s"' % column)
                            quoted_col = '.'.join(parts)
                        else:
                            quoted_col = column
                    if self.as_columns[i]:
                        quoted_col = '%s as "%s"' % (quoted_col, self.as_columns[i])
                    quoted_cols.append(quoted_col)
                statement.append(', '.join(quoted_cols))
            if database_type == 'SQLServer' and self.limit != None:
                order_by = 'ORDER BY id'
                order_bys = []
                for order_by in self.order_bys:
                    if order_by.startswith('( CASE'):
                        order_bys.append(order_by)
                    elif regex_asc.search(order_by) or regex_desc.search(order_by):
                        parts = order_by.split(' ')
                        parts[0] = parts[0].strip('"')
                        parts[0] = '"%s"' % parts[0]
                        order_bys.append(' '.join(parts))
                    elif database_type == 'SQLServer':
                        order_by = order_by.strip('"')
                        order_bys.append('"%s"' % order_by)
                if order_bys:
                    order_by = 'ORDER BY %s' % ', '.join(order_bys)
                statement.append(', ROW_NUMBER() over(%s) as %s ' % (order_by, self.impl.get_temp_column_name()))
        if not self.tables:
            raise SqlException('No tables defined')
        clauses = []
        if self.tables[0].startswith('('):
            clauses.append('FROM %s' % self.tables[0])
        elif self.database and is_oracle:
            clauses.append('FROM ' + ', '.join(['"%s"."%s"' % (self.database, x) for x in self.tables]))
        else:
            tables = []
            for table in self.tables:
                if self.quoted_mode == 'none':
                    tables.append(table)
                    continue
                parts = []
                if self.database:
                    parts.append(self.database)
                if self.schema:
                    parts.append(self.schema)
                parts.append(table)
                table = '.'.join(['"%s"' % x for x in parts])
                tables.append(table)
            clauses.append('FROM ' + ', '.join(tables))
        if self.joins:
            clauses.extend(self.joins)
        if len(self.filters):
            filters = self.filters.values()
            expanded = []
            for filter in filters:
                if len(filter) == 1:
                    expr = filter[0]
                else:
                    expr = '(%s)' % (' %s ' % self.filter_mode).join(filter)
                expanded.append(expr)
            self.wheres = expanded
        if len(self.wheres) > 0:
            wheres_copy = self.wheres[:]
            new_expr = self.process_wheres(wheres_copy)
            if new_expr:
                clauses.append('WHERE %s' % new_expr)
        if mode == 'normal':
            if len(self.group_bys) > 0:
                for item in self.order_bys:
                    if regex_asc.search(item) or regex_desc.search(item):
                        parts = item.split(' ')
                        item = parts[0]
                    if item not in self.group_bys:
                        self.group_bys.append(item)
                group_by_stmt = ', '.join(['"%s"' % x for x in self.group_bys])
                clauses.append('GROUP BY %s' % group_by_stmt)
            if len(self.havings) > 0:
                clauses.append('HAVING %s' % ' AND '.join(self.havings))
            if not self.distinct and len(self.order_bys) > 0:
                order_bys = []
                for order_by in self.order_bys:
                    if order_by.startswith('( CASE'):
                        order_bys.append(order_by)
                    elif (regex_asc.search(order_by) or regex_desc.search(order_by)) and order_by.find('->') == -1:
                        parts = order_by.split(' ')
                        parts[0] = parts[0].strip('"')
                        parts[0] = '"%s"' % parts[0]
                        order_bys.append(' '.join(parts))
                    elif database_type == 'SQLServer':
                        order_by = order_by.strip('"')
                        order_bys.append('"%s"' % order_by)
                    elif order_by.find('->') != -1:
                        print('order: ', order_by)
                        order_bys.append('"%s".%s' % (self.tables[0], order_by))
                    elif order_by.find('.') == -1:
                        order_bys.append('"%s"."%s"' % (self.tables[0], order_by))
                    else:
                        order_bys.append(order_by)
                clauses.append('ORDER BY %s' % ', '.join(order_bys))
            if database_type not in ['Oracle', 'SQLServer']:
                page = self.impl.get_page(self.limit, self.offset)
                if page:
                    clauses.append(page)
        clause = ' '.join(clauses)
        statement.append(clause)
        statement = ' '.join(statement)
        if mode != 'count' and self.limit != None:
            if database_type in ['Oracle', 'SQLServer']:
                statement = self.impl.handle_pagination(statement, self.limit, self.offset)
        return statement

    def process_wheres(self, wheres):
        if not wheres:
            return
        if wheres[0] != 'begin':
            wheres.insert(0, 'begin')
        if wheres[-1].lower() not in ['and', 'or']:
            wheres.append('and')
        count_begin = 0
        count_op = 0
        level = 0
        num_paren_groups = 0
        for item in wheres:
            if item == 'begin':
                count_begin += 1
                if level == 0:
                    num_paren_groups += 1
                level += 1
            elif item in ['and', 'or']:
                count_op += 1
                level -= 1
        if count_begin > count_op:
            wheres.append('and')
        cur_stack = []
        self.stack_index = 0
        while self.stack_index < len(wheres):
            expr = self._handle_stack_item(cur_stack, wheres)
            cur_stack = [expr]
        if not expr:
            return None
        if num_paren_groups == 1 and expr.startswith('( ') and expr.endswith(' )'):
            expr = expr[2:-2]
        return expr

    def _handle_stack_item(self, cur_stack, wheres):
        while 1:
            if self.stack_index >= len(wheres):
                return ' AND '.join(cur_stack)
            item = wheres[self.stack_index]
            self.stack_index += 1
            if item == 'begin':
                new_stack = []
                cur_stack.append(new_stack)
                expr = self._handle_stack_item(new_stack, wheres)
                cur_stack.pop()
                if expr:
                    cur_stack.append(expr)
            elif item in ['and', 'or']:
                if not cur_stack:
                    expr = None
                elif len(cur_stack) == 1:
                    expr = cur_stack[0]
                else:
                    op = ' %s ' % item.upper()
                    expr = '( %s )' % op.join(cur_stack)
                return expr
            elif item:
                cur_stack.append(item)

    def get_count(self):
        if self.group_bys or self.havings or self.distinct or self._statement:
            select = self.copy()
            select.limit, select.offset = (None, 0)
            select.order_bys, select.order_by_columns = ([], [])
            return 'SELECT count(*) FROM (%s) AS spt_count' % select.get_statement()
        return self.get_statement(mode='count')

    def get_interval_where(time_interval, name='timestamp'):
        """ get the where sql statement for search """
        from pyasm.biz import Project
        impl = Project.get_database_impl()
        database_type = impl.get_database_type()
        time_interval = time_interval.lower()
        if database_type == 'Oracle':
            if time_interval == 'today':
                return '"%s" >= TO_TIMESTAMP(SYSDATE)' % name
            else:
                offset, unit = time_interval.split(' ')
                if unit in ['week', 'Week']:
                    unit = 'day'
                    offset = int(offset) * 7
                return '"%s" >= SYSTIMESTAMP - INTERVAL \'%s\' %s' % (name, offset, unit)
        elif database_type == 'SQLServer':
            if time_interval == 'today':
                return '%s >= CONVERT(date, GETDATE())' % name
            else:
                offset_time, unit = time_interval.split()
                offset = impl.get_timestamp_now(offset=offset_time, type=unit, op='-')
                return '%s >=  %s' % (name, offset)
            "\n            elif time_interval.lower() == '1 hour':\n                return  '%s >= DATEADD(hour,-1, GETDATE())' %(name)\n            elif time_interval.lower() == '1 day':\n                return  '%s >= DATEADD(day,-1, GETDATE())' %(name)\n            elif time_interval.lower() == '1 week':\n                return  '%s >= DATEADD(week,-1, GETDATE())' %(name)\n            elif time_interval.lower() == '1 month':\n                return  '%s >= DATEADD(month,-1, GETDATE())' %(name)\n            "
        elif database_type == 'MySQL':
            if time_interval == 'today':
                return '%s >= CURDATE()' % name
            else:
                offset_time, unit = time_interval.split()
                offset_time = int(offset_time)
                offset = impl.get_timestamp_now(offset=offset_time, type=unit, op='-')
                return '%s >= %s' % (name, offset)
        elif database_type == 'Sqlite':
            if time_interval == 'today':
                return "%s >= date('now')" % name
            else:
                offset_time, unit = time_interval.split()
                offset_time = int(offset_time)
                offset = impl.get_timestamp_now(offset=offset_time, type=unit, op='-')
                return '%s >= %s' % (name, offset)
        elif time_interval == 'today':
            return "%s >= 'today'::timestamp" % name
        else:
            return "%s >= now() - '%s'::interval" % (name, time_interval)
    get_interval_where = staticmethod(get_interval_where)


class DbResource(Base):
    DBRESOURCE_ID = "DbResource"

    def __init__(self, database, host=None, port=None, vendor=None, user=None, password=None, schema=None, **options):
        from pyasm.search.search import _context
        assert database
        if vendor not in (None, "", "Sqlite", 'PostgreSQL'):
            raise UnsupportedContract("Database resource vendor is not migrated: %s" % vendor)
        if vendor != 'PostgreSQL':
            if host not in (None, '', 'localhost'):
                raise UnsupportedContract('SQLite resources must be local')
            _context.get().store.database_path(database)
        elif not isinstance(database, str) or '\x00' in database:
            raise ValueError('Invalid PostgreSQL database name')
        self.database = database
        self.host = host or "localhost"
        self.port, self.user, self.password, self.schema = port, user, password, schema
        self.vendor, self.options = vendor or "Sqlite", options

    def __str__(self):
        return "DbResource:%s:%s:%s:%s:%s" % (self.vendor, self.host, self.port, self.schema, self.database)

    def get_database(self):
        return self.database

    def get_host(self):
        return self.host

    def get_port(self):
        return self.port

    def get_vendor(self):
        return self.vendor

    def get_user(self):
        return self.user

    def get_password(self):
        return self.password

    def get_schema(self):
        return self.schema

    def get_key(self):
        return "%s:%s:%s:%s:%s" % (self.vendor, self.host, self.port, self.schema, self.database)

    def _get_connection_key(self):
        credentials = (self.user, self.password, sorted(self.options.items()))
        return self.get_key(), sha256(repr(credentials).encode()).digest()

    def get_database_type(self):
        return self.vendor

    def get_database_impl(self):
        from pyasm.search.database_impl import DatabaseImpl
        return DatabaseImpl.get(self.vendor)

    def get_sql(self):
        return DbContainer.get(self)

    @staticmethod
    def is_instance(inst):
        return hasattr(inst, "DBRESOURCE_ID")

    @classmethod
    def get_default(cls, database, schema="public", use_cache=True, use_config=False):
        if not database:
            raise Exception("DbResource.get_default called with empty database/project code")
        cache = Container.get("Project:db_resource_cache")
        if not cache:
            cache = {}
            if use_cache:
                Container.put("Project:db_resource_cache", cache)
        key = "%s:%s" % (database, schema)
        if use_cache and key in cache:
            return cache[key]
        from pyasm.common.config import Config
        vendor = Config.get_value('database', 'vendor', default='Sqlite')
        if vendor == 'PostgreSQL':
            from pathlib import Path
            if database == 'sthpw':
                database = Config.get_value('database', 'sobject_database', default='sthpw')
            password_file = Config.get_value('database', 'password_file')
            password = Path(password_file).read_text(encoding='utf-8').strip() if password_file else Config.get_value('database', 'password')
            resource = cls(database, host=Config.get_value('database', 'host') or Config.get_value('database', 'server'),
                           port=Config.get_value('database', 'port'),
                           vendor=vendor, user=Config.get_value('database', 'user'), password=password, schema=schema)
        elif vendor.lower() == 'sqlite':
            resource = cls(database, port="", user="", password="", schema=schema)
        else:
            raise UnsupportedContract('Database resource vendor is not migrated: %s' % vendor)
        if use_cache:
            cache[key] = resource
        return resource

    @classmethod
    def get_by_code(cls, code, database):
        from pyasm.search.search import _context
        from pyasm.common.common import TacticException
        # Project routing needs server-side credentials for ordinary users too;
        # direct client/expression reads of this table retain their admin guard.
        store = _context.get().store
        parameter = store.get_db_resource().get_database_impl().get_parameter()
        with store.connection() as db:
            row = db.execute('SELECT host,port,vendor,login,password FROM db_resource WHERE code=' + parameter, (code,)).fetchone()
            resource = dict(row) if row else None
        if resource is None:
            raise TacticException('Database Resource [%s] does not exist' % code)
        return cls(database, host=resource['host'], port=resource['port'],
                   vendor=resource['vendor'], user=resource['login'], password=resource['password'])

    @classmethod
    def clear_cache(cls):
        Container.put("Project:db_resource_cache", None)


class Sql(Base):
    DO_QUERY_ERR = "do_query error"

    def __init__(self, database_name, host=None, user=None, password=None, vendor=None, port=None):
        from pyasm.search.search import _context
        self._db_resource = database_name if DbResource.is_instance(database_name) else None
        if self._db_resource is None and all(value is None for value in (host, user, password, vendor, port)):
            self._db_resource = DbResource.get_default(database_name)
        if self._db_resource:
            resource = self._db_resource
            database_name, host, port = resource.get_database(), resource.get_host(), resource.get_port()
            user, password, vendor = resource.get_user(), resource.get_password(), resource.get_vendor()
        if vendor not in (None, "", "Sqlite", 'PostgreSQL'):
            raise UnsupportedContract("Database connection vendor is not migrated: %s" % vendor)
        if vendor != 'PostgreSQL' and host not in (None, '', 'localhost'):
            raise UnsupportedContract('SQLite connections must be local')
        self.database_name = database_name
        self.host, self.port, self.user, self.password = host or "localhost", port, user, password
        self.vendor = vendor or "Sqlite"
        self.cursor = self.conn = self.description = self.last_query = None
        self.results = ()
        self.row_count = -1
        self.transaction_count = 0
        self._context = _context.get()
        self._read_depth = 0
        self._has_writes = False
        self._errors, self._operational_errors = (sqlite3.Error,), (sqlite3.OperationalError,)
        from pyasm.search.database_impl import DatabaseImpl
        self.database_impl = DatabaseImpl.get(self.vendor)

    def get_db_resource(self):
        return self._db_resource or DbResource(self.database_name, host=self.host, port=self.port,
                                              vendor=self.vendor, user=self.user, password=self.password)

    def get_database_name(self):
        return self.database_name

    def get_database_type(self):
        return self.vendor

    def get_vendor(self):
        return self.vendor

    def get_database_impl(self):
        return self.database_impl

    def get_timestamp_now(self):
        return self.get_database_impl().get_timestamp_now()

    @staticmethod
    def get_default_timestamp_now():
        from pyasm.search.database_impl import DatabaseImpl
        return DatabaseImpl.get().get_timestamp_now()

    @staticmethod
    def get_default_database_impl():
        from pyasm.search.database_impl import DatabaseImpl
        return DatabaseImpl.get()

    def get_host(self):
        return self.host

    def get_user(self):
        return self.user

    def get_password(self):
        return self.password

    def get_connection(self):
        return self.conn

    def get_row_count(self):
        return self.row_count

    def check_schema_write(self):
        from pyasm.search.transaction import Transaction
        from pyasm.search.search import _context
        from pyasm.security.security import _require_admin
        _require_admin()
        transaction = Transaction.get()
        if transaction is None or not transaction.is_in_transaction():
            raise UnsupportedContract('Schema changes require an active Command/Transaction')
        if not transaction.can_write_resource(self.get_db_resource()):
            raise UnsupportedContract('Schema changes require the system or a registered project database')

    @staticmethod
    def clear_table_cache(database=None):
        Container.clear_dict('DatabaseImpl:column_info')
        Container.clear_dict('DatabaseImpl:table_info')
        Container.clear_dict('SearchType:column_info')
        Container.clear_dict('Store:resolve')
        from pyasm.search.search import _context
        context = _context.get(None)
        if context is not None:
            for schema in context.schemas.values():
                schema.relationships.clear()
        for key in list(Container.get_instance().get_data()):
            if isinstance(key, str) and key.endswith('::cached_obj'):
                Container.clear_dict(key)

    def add_column(self, table, column, data_type):
        self.check_schema_write()
        self.database_impl.validate_data_type(data_type)
        self.do_update('ALTER TABLE %s ADD COLUMN %s %s' %
                       (identifier(table), identifier(column), data_type))
        self.clear_table_cache(self.database_name)

    def create_index(self, table, columns, name):
        """Native schema API shared by SQLite and PostgreSQL."""
        self.check_schema_write()
        if not columns:
            raise ValueError('Index columns required')
        target = identifier(table)
        if self.vendor == 'PostgreSQL':
            target = identifier(self.get_db_resource().get_schema()) + '.' + target
        self.do_update('CREATE INDEX ' + identifier(name) + ' ON ' + target +
                       ' (' + ', '.join(identifier(column) for column in columns) + ')')
        self.clear_table_cache(self.database_name)

    def copy_table_schema(self, from_table, to_table):
        self.check_schema_write()
        identifier(from_table)
        identifier(to_table)
        if self.database_impl.table_exists(self.get_db_resource(), to_table):
            raise DatabaseException('Destination table already exists: ' + to_table)
        self.database_impl.copy_table_schema(self, from_table, to_table)
        self.clear_table_cache(self.database_name)

    def drop_column(self, table, column):
        self.check_schema_write()
        self.do_update('ALTER TABLE %s DROP COLUMN %s' % (identifier(table), identifier(column)))
        self.clear_table_cache(self.database_name)
        from .transaction import Transaction, TableUndo
        transaction = Transaction.get()
        if transaction and not Container.get('is_undo'):
            for node in reversed(transaction.get_xml().get_nodes('transaction/alter')):
                if (node.get('action') == 'drop' and node.get('database') == self.database_name
                        and node.get('table') == table and node.get('column') == column
                        and node.find('remaining') is None):
                    TableUndo._save(node, 'remaining', self.database_impl.get_table_definition(self, table))
                    break

    def table_exists(self, table):
        db_resource = self.get_db_resource()
        return self.database_impl.table_exists(db_resource, table)

    def get_column_info(self, table, column=None, use_cache=True):
        impl = self.get_database_impl()
        info = impl.get_column_info(self.get_db_resource(), table, use_cache=use_cache)
        if not column:
            return info
        else:
            return info.get(column)

    def get_column_types(self, table):
        impl = self.get_database_impl()
        return impl.get_column_types(self.get_db_resource(), table)

    def is_in_transaction(self):
        '''Returns a boolean showing whether the database is in transaction
        or not'''
        if self.transaction_count <= 0:
            return False
        else:
            return True

    def get_table_description(self):
        return self.description

    def get_columns_from_description(self):
        return [item[0].split(".")[-1].strip('"') for item in self.description]

    def _check_context(self):
        from pyasm.search.search import _context
        current = _context.get()
        if (current.container is not self._context.container or current.store is not self._context.store or
                current.login != self._context.login):
            raise UnsupportedContract("SQL connections cannot cross request contexts")

    def connect(self):
        self._check_context()
        from pyasm.security.authenticator import Authenticator
        store = self._context.store
        # Auth must not recursively enter Store's transaction-aware read path.
        system = store.get_db_resource()
        postgres = system.get_vendor() == 'PostgreSQL'
        identity_key = ('Sql:identity', system._get_connection_key()) if postgres else 'sthpw'
        db = self._context.read_connections.get(identity_key)
        if db is None:
            db = (system.get_database_impl()._connect(system) if postgres else
                  sqlite3.connect(store.database_path('sthpw').as_uri() + '?mode=ro', uri=True))
            self._context.read_connections[identity_key] = db
            if not postgres:
                system.get_database_impl().configure_connection(db)
                db.row_factory = sqlite3.Row
                db.execute('PRAGMA query_only=ON')
        try:
            if postgres:
                db.execute('SET TRANSACTION READ ONLY')
            marker = '%s' if postgres else '?'
            active_login = db.execute('SELECT 1 FROM login WHERE login=' + marker +
                                      " AND (s_status IS NULL OR s_status!='retired')", (self._context.login,)).fetchone()
            self._admin_sql = Authenticator._admin(db, self._context.login, marker, active=bool(active_login))
        finally:
            # Reuse the connection, never an identity result or a PostgreSQL snapshot.
            if postgres:
                db.rollback()
        from pyasm.search.transaction import Transaction
        transaction = Transaction.get()
        object_transaction = active_login and transaction is not None and transaction.is_in_transaction()
        if not self._admin_sql and not active_login and not (
                self.vendor == 'Sqlite' and ((self.database_name == 'sthpw' and Container.get('Security:writing'))
                or (active_login and (Container.get('Chat:writing') or Container.get('UserProfile:writing')))
                or object_transaction)):
            raise UnsupportedContract("Native SQL connections require an active account")
        if self.vendor == 'PostgreSQL':
            try:
                import psycopg
            except ImportError:
                raise UnsupportedContract('Install tactic-stream[postgres] to use PostgreSQL') from None
            self._errors, self._operational_errors = (psycopg.Error,), (psycopg.OperationalError,)
            options = dict(self.get_db_resource().options)
            if set(options) & {'autocommit', 'row_factory', 'cursor_factory', 'context', 'prepare_threshold'}:
                raise UnsupportedContract('PostgreSQL connection options cannot override native transaction/cursor behavior')
            options.setdefault('connect_timeout', 5)
            try:
                self.conn = psycopg.connect(dbname=self.database_name, host=self.host, port=self.port or 5432,
                                            user=self.user, password=self.password, **options)
                schema = self.get_db_resource().get_schema() or 'public'
                self.conn.execute(psycopg.sql.SQL('SET search_path TO {}').format(psycopg.sql.Identifier(schema)))
                self.conn.commit()
            except psycopg.Error as exc:
                if self.conn is not None:
                    self.conn.close()
                    self.conn = None
                raise DatabaseException('PostgreSQL connection failed: %s' % exc) from exc
        else:
            self.conn = sqlite3.connect(store.database_path(self.database_name).as_uri() + "?mode=rw",
                                        uri=True, timeout=5, isolation_level="DEFERRED")
            self.get_database_impl().configure_connection(self.conn)
            self.conn.set_authorizer(self._authorize)
        Container.append_seq("DbContainer:sql_seq", self)
        return self

    @staticmethod
    def _system_write_tables():
        tables = ()
        profile = Container.get('UserProfile:writing')
        if profile:
            tables += ('login', 'ticket', 'transaction_log', 'sobject_log', 'change_timestamp')
            if profile['manage']: tables += ('login_group', 'login_in_group')
            if profile['avatar']: tables += ('snapshot', 'file')
        if Container.get('Security:writing'):
            tables += ('login', 'ticket', 'transaction_log', 'sobject_log', 'change_timestamp')
        if Container.get('Chat:writing'):
            tables += ('message', 'message_log', 'subscription', 'connection',
                       'transaction_log', 'sobject_log', 'change_timestamp')
        if Container.get('Chat:attachment'):
            tables += ('snapshot', 'file')
        return tables

    def _authorize(self, action, first, second, database, source):
        if getattr(self, '_file_marker_write', False) and first in ('_stream_file_commits', 'sqlite_master', 'sqlite_autoindex__stream_file_commits_1'):
            return sqlite3.SQLITE_OK
        if not self._admin_sql and action in (
                sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_ALTER_TABLE,
                sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_INDEX,
                sqlite3.SQLITE_CREATE_TRIGGER, sqlite3.SQLITE_DROP_TRIGGER,
                sqlite3.SQLITE_CREATE_VIEW, sqlite3.SQLITE_DROP_VIEW,
                sqlite3.SQLITE_CREATE_TEMP_TABLE, sqlite3.SQLITE_CREATE_TEMP_INDEX,
                sqlite3.SQLITE_CREATE_TEMP_TRIGGER, sqlite3.SQLITE_CREATE_TEMP_VIEW,
                sqlite3.SQLITE_DROP_TEMP_TABLE, sqlite3.SQLITE_DROP_TEMP_INDEX,
                sqlite3.SQLITE_DROP_TEMP_TRIGGER, sqlite3.SQLITE_DROP_TEMP_VIEW,
                sqlite3.SQLITE_CREATE_VTABLE, sqlite3.SQLITE_DROP_VTABLE):
            return sqlite3.SQLITE_DENY
        if not self._admin_sql and action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
            if first == getattr(self, '_sobject_write_table', None):
                pass
            elif (self.get_db_resource()._get_connection_key() != self._context.store.get_db_resource()._get_connection_key()
                    or first not in self._system_write_tables()):
                return sqlite3.SQLITE_DENY
        if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_FUNCTION and second == "load_extension":
            return sqlite3.SQLITE_DENY
        if self._read_depth:
            if action == sqlite3.SQLITE_PRAGMA:
                read_pragmas = {"table_info", "table_xinfo", "index_list", "index_info", "foreign_key_list", "database_list"}
                if second is not None and first not in read_pragmas:
                    return sqlite3.SQLITE_DENY
            elif action not in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE):
                return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    @contextmanager
    def read_connection(self):
        self._check_context()
        if self.conn is None:
            self.connect()
        if self.vendor == 'PostgreSQL':
            name = 'stream_read_' + uuid.uuid4().hex
            self.conn.execute('SAVEPOINT ' + name)
            reader = _PostgresReadConnection(self)
            self._read_depth += 1
            try:
                self.conn.execute('SET LOCAL transaction_read_only = on')
                yield reader
            finally:
                try:
                    reader._close_cursors()
                finally:
                    self._read_depth -= 1
                    # Abort the read subtransaction, including GUC changes and errors.
                    # Pending outer writes remain visible and writable afterwards.
                    self.conn.execute('ROLLBACK TO SAVEPOINT ' + name)
                    self.conn.execute('RELEASE SAVEPOINT ' + name)
                    if not self._read_depth and not self.transaction_count:
                        self.conn.rollback()
            return
        self._read_depth += 1
        previous_factory = self.conn.row_factory
        self.conn.row_factory = sqlite3.Row
        # Reauthorize cached statements when changing between read and write scopes.
        self.conn.set_authorizer(self._authorize)
        try:
            yield self.conn
        finally:
            self._read_depth -= 1
            self.conn.row_factory = previous_factory
            self.conn.set_authorizer(self._authorize)

    def _lock_snapshot_versions(self):
        self._check_context()
        if self.conn is None:
            self.connect()
        if self._read_depth or not self.transaction_count or not (self._admin_sql or Container.get('Chat:attachment') or (Container.get('UserProfile:writing') or {}).get('avatar') or Container.get('Checkin:writing')):
            raise UnsupportedContract("Snapshot version allocation requires a trusted write transaction")
        if Container.get('Checkin:writing'):
            from pyasm.search.transaction import FileUndo
            FileUndo._check_access()
        # ponytail: table-wide lock; narrow to parent/context if check-in throughput needs it.
        if self.vendor == 'PostgreSQL':
            self.conn.execute('LOCK TABLE "snapshot" IN SHARE ROW EXCLUSIVE MODE')
        elif not self.conn.in_transaction:
            self.conn.execute('BEGIN IMMEDIATE')

    def lock_sobject(self, sobject, timeout=None):
        """Lock an authorized native row in the current write transaction."""
        self._check_context()
        sobject._check_business_write('edit')
        from pyasm.search.transaction import Transaction
        transaction = Transaction.get()
        if self._read_depth or not transaction.is_in_transaction() or sobject.get_id() == -1:
            raise UnsupportedContract('Row locking requires a persistent SObject and a transaction')
        if sobject.get_db_resource()._get_connection_key() != self.get_db_resource()._get_connection_key():
            raise UnsupportedContract('Row belongs to another database')
        transaction.check_write_resource(self.get_db_resource())
        if self.conn is None:
            self.connect()
        transaction.register_database(self)
        if self.vendor == 'PostgreSQL':
            if timeout is not None:
                if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 60000:
                    raise ValueError('Row lock timeout must be 1..60000 milliseconds')
                self.conn.execute("SELECT set_config('lock_timeout', %s, true)", (str(timeout) + 'ms',))
            target = identifier(self.get_db_resource().get_schema()) + '.' + identifier(sobject.get_table())
            with self.conn.cursor() as cursor:
                cursor.execute('SELECT id FROM ' + target + ' WHERE id=%s FOR UPDATE', (sobject.get_id(),))
        elif not self.conn.in_transaction:
            self.conn.execute('BEGIN IMMEDIATE')

    def lock_queue(self):
        """Serialize native queue claims/manifests before publishing file readiness."""
        self._check_context()
        if self.conn is None:
            self.connect()
        if self._read_depth or not self.transaction_count or not (self._admin_sql or Container.get('CheckinQueue:locking')):
            raise UnsupportedContract('Queue locking requires a trusted write transaction')
        if self.vendor == 'PostgreSQL':
            self.conn.execute('LOCK TABLE "queue" IN SHARE ROW EXCLUSIVE MODE')
        elif not self.conn.in_transaction:
            self.conn.execute('BEGIN IMMEDIATE')

    def lock_transaction_state(self, ticket):
        self._check_context()
        if self.conn is None:
            self.connect()
        if self._read_depth or not self.transaction_count:
            raise UnsupportedContract('Transaction state locking requires a write transaction')
        if self.vendor == 'PostgreSQL':
            with self.conn.cursor() as cursor:
                # Lock the ticket even before its state row has been created.
                cursor.execute('SELECT id FROM ticket WHERE ticket=%s FOR UPDATE', (ticket,))
        elif not self.conn.in_transaction:
            self.conn.execute('BEGIN IMMEDIATE')

    def lock_workflow_state(self):
        self._check_context()
        if self._read_depth or not self.transaction_count:
            raise UnsupportedContract('Workflow state locking requires a write transaction')
        if getattr(self, '_workflow_locked', False):
            return
        if self.conn is None:
            self.connect()
        # ponytail: serialize Workflow writes; use per-object locks if throughput requires it.
        if self.vendor == 'PostgreSQL':
            self.conn.execute('LOCK TABLE "spt_process_state" IN SHARE ROW EXCLUSIVE MODE')
        elif not self.conn.in_transaction:
            self.conn.execute('BEGIN IMMEDIATE')
        self._workflow_locked = True

    def lock_transaction_log(self, log_id):
        self._check_context()
        if self.conn is None:
            self.connect()
        if self._read_depth or not self.transaction_count:
            raise UnsupportedContract('Journal locking requires a write transaction')
        if self.vendor == 'PostgreSQL':
            self.conn.execute('SELECT id FROM transaction_log WHERE id=%s FOR UPDATE', (log_id,))
        elif not self.conn.in_transaction:
            self.conn.execute('BEGIN IMMEDIATE')

    def start(self):
        self._check_context()
        if self._read_depth:
            raise UnsupportedContract('Cannot start a write transaction inside a read scope')
        self.transaction_count += 1

    def _record_file_commit(self, token):
        """Internal commit evidence; the marker joins the existing native transaction."""
        from pyasm.search.transaction import Transaction
        transaction = Transaction.get()
        self._check_context()
        if (self._read_depth or not transaction or not transaction.file_journal or
                transaction.file_journal.token != token or self not in transaction.get_databases().values()):
            raise UnsupportedContract('File commit evidence requires its owning transaction')
        self._file_marker_write = True
        try:
            if self.vendor == 'PostgreSQL':
                # Concurrent first use must not race the catalog's unique table name.
                if not self.conn.execute("SELECT to_regclass('_stream_file_commits')").fetchone()[0]:
                    self.conn.execute("SELECT pg_advisory_xact_lock(71629401)")
                    self.conn.execute('CREATE TABLE IF NOT EXISTS _stream_file_commits (token varchar(32) PRIMARY KEY)')
            else:
                self.conn.execute('CREATE TABLE IF NOT EXISTS _stream_file_commits (token varchar(32) PRIMARY KEY)')
            marker = self.get_database_impl().get_parameter()
            self.conn.execute('INSERT INTO _stream_file_commits (token) VALUES (' + marker + ')', (token,))
            self._has_writes = True
        finally:
            self._file_marker_write = False
            if self.vendor == 'Sqlite':
                self.conn.set_authorizer(self._authorize)

    def commit(self):
        self._check_context()
        if self._read_depth:
            raise UnsupportedContract('Cannot commit inside a read scope')
        self.transaction_count -= 1
        if self.transaction_count <= 0:
            self.transaction_count = 0
            try:
                if self.conn is None:
                    self.connect()
                else:
                    self.conn.commit()
                self._has_writes = False
                self._workflow_locked = False
                DbContainer._get_sql_dict()[self.get_database_name()] = self
            except self._errors as exc:
                # Keep rollback available when SQLite refuses a commit.
                self.transaction_count = 1
                raise SqlException(str(exc)) from exc

    def _clear_file_commit(self, token):
        from pyasm.search.search import _context
        path = _context.get().store.data_dir / 'temp' / 'file-transactions' / (token + '.jsonl')
        if self.transaction_count or self._read_depth or path.exists():
            raise UnsupportedContract('Cannot remove evidence for an unresolved file transaction')
        self._check_context()
        if self.conn is None:
            self.connect()
        self._file_marker_write = True
        try:
            marker = self.get_database_impl().get_parameter()
            self.conn.execute('DELETE FROM _stream_file_commits WHERE token=' + marker, (token,))
            self.conn.commit()
        except self._errors:
            self.conn.rollback()
            import logging
            logging.getLogger(__name__).exception('Resolved file commit marker cleanup deferred')
        finally:
            self._file_marker_write = False
            if self.vendor == 'Sqlite':
                self.conn.set_authorizer(self._authorize)

    def rollback(self, force=False):
        self._check_context()
        if self._read_depth:
            raise UnsupportedContract('Cannot roll back the outer transaction inside a read scope')
        if force or self.transaction_count > 0:
            if self.conn is not None:
                self.conn.rollback()
                self.transaction_count = 0
                self._has_writes = False
                self._workflow_locked = False
                self.clear_table_cache()

    def close(self):
        self._check_context()
        if self._read_depth:
            raise UnsupportedContract('Cannot close the outer connection inside a read scope')
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            self._has_writes = False
            self._workflow_locked = False

    def clear_results(self):
        self.results = []

    def do_query(self, query, num_attempts=0):
        if isinstance(query, Select):
            owner = getattr(query, '_search_owned', None)
            if owner and not owner._same_database(self.get_db_resource()):
                raise UnsupportedContract('Execute a Search Select on its own database resource')
            query = query.get_statement()
        if not isinstance(query, str):
            raise TypeError('Query must be SQL text or a Select')
        self.clear_results()
        self.query = query
        try:
            with self.read_connection() as db:
                self.cursor = db.cursor()
                try:
                    self.cursor.execute(query)
                    self.description = self.cursor.description
                    self.results = [tuple(row) for row in self.cursor.fetchall()]
                finally:
                    self.cursor.close()
            return self.results
        except self._operational_errors as exc:
            # Reconnecting here could discard an active transaction. No retries.
            raise SqlException("%s: %s\n%s" % (self.DO_QUERY_ERR, query, str(exc))) from exc
        except self._errors as exc:
            raise SqlException("%s: %s\n" % (self.DO_QUERY_ERR, query)) from exc

    def get_value(self, query):
        result = self.do_query(query)
        value = result[0][0] if result else ""
        return "" if value is None else value

    def get_int(self, query):
        return int(self.get_value(query))

    def do_update(self, query, quiet=False):
        return self._do_update(query, quiet)

    @staticmethod
    def _native_metadata_table(table, data=None, unquoted=()):
        from decimal import Decimal
        for name in unquoted:
            value = data[name]
            if (value is not None and not isinstance(value, (bool, int, float, Decimal)) and
                    value not in ('NULL', 'CURRENT_TIMESTAMP', 'NOW()')):
                return None  # Custom SQL expressions may change registry/schema through a function.
        return table

    def _do_security_dml(self, table, data=None, id_col=None, search_id=None, unquoted=(), sobject=None):
        query, parameters, object_write = self._prepare_security_dml(table, data, id_col, search_id, unquoted, sobject)
        previous = getattr(self, '_sobject_write_table', None)
        try:
            if object_write:
                self._sobject_write_table = table
            return self._do_update(query, parameters=parameters, security_write=True,
                                   native_table=self._native_metadata_table(table, data, unquoted) if object_write else None)
        finally:
            self._sobject_write_table = previous
            if self.vendor == 'Sqlite':
                self.conn.set_authorizer(self._authorize)

    def _prepare_security_dml(self, table, data=None, id_col=None, search_id=None, unquoted=(), sobject=None, insert_count=1):
        """Bound native writes for ordinary users, after SObject checks."""
        from decimal import Decimal
        from pyasm.search.storage import identifier
        if self.conn is None:
            self.connect()
        system = self._context.store.get_db_resource()
        object_write = self._admin_sql and sobject is not None
        if sobject is not None and not self._admin_sql:
            from pyasm.common import Environment
            from pyasm.search import SObject, Transaction
            transaction = Transaction.get()
            security = Environment.get_security()
            if (not isinstance(sobject, SObject) or security is None or
                    security.get_user_name() != self._context.login or
                    transaction is None or not transaction.is_in_transaction() or
                    not transaction.can_write_resource(self.get_db_resource()) or
                    sobject.get_db_resource()._get_connection_key() != self.get_db_resource()._get_connection_key() or
                    sobject.get_table() != table or (data is None and id_col is None) or (id_col is not None and
                    (sobject.get_id_col() != id_col or sobject.get_id() != search_id))):
                raise UnsupportedContract('Native object writes require their own authenticated Command resource')
            base = sobject.get_base_search_type()
            if base in ('sthpw/task', 'sthpw/note') or not base.startswith(('sthpw/', 'config/')):
                sobject._check_business_write('delete' if data is None else 'insert' if id_col is None else 'edit')
                if base == 'sthpw/note' and any(value != sobject.get_value(name, no_exception=True) and
                        not (value == 'NULL' and sobject.get_value(name, no_exception=True) is None)
                        for name, value in (data or {}).items()):
                    raise UnsupportedContract('Note SQL must match its own staged record')
                for name in data or ():
                    project = sobject.get_value('project_code') if base in ('sthpw/task', 'sthpw/note') else sobject.get_project_code()
                    key = {'search_type': base, 'column': name, 'project': project}
                    if not security.check_access('sobject_column', key, 'edit'):
                        from pyasm.common.errors import SecurityException
                        raise SecurityException('Column [%s] not editable for search type [%s]' % (name, sobject.get_search_type()))
                object_write = True
            elif base == 'sthpw/queue' and Container.get('CheckinQueue:writing') is sobject:
                sobject._check_business_write('delete' if data is None else 'insert' if id_col is None else 'edit')
                if data is None:
                    raise UnsupportedContract('Check-in queue records cannot be deleted by their submitter')
                for name, value in data.items():
                    expected = sobject.get_value(name, no_exception=True)
                    if isinstance(expected, (dict, list)) and isinstance(value, str):
                        value = jsonloads(value)
                    if value != expected and not (value == 'NULL' and expected is None):
                        raise UnsupportedContract('Queue SQL must match its own staged record')
                object_write = True
            elif base in ('sthpw/snapshot', 'sthpw/file') and Container.get('Checkin:writing'):
                project = sobject._check_repository_write('delete' if data is None else 'insert' if id_col is None else 'edit')
                for name, value in (data or {}).items():
                    expected = sobject.get_value(name, no_exception=True)
                    if isinstance(expected, (dict, list)) and isinstance(value, str):
                        value = jsonloads(value)
                    if value != expected and not (value == 'NULL' and expected is None):
                        raise UnsupportedContract('Repository SQL must match its own staged record')
                object_write = True
            elif Container.get('Workflow:replay') and base in ('config/process_state', 'sthpw/status_log', 'sthpw/message', 'sthpw/message_log'):
                from pyasm.command.workflow import _check_replay_effect
                project = _check_replay_effect(sobject, 'delete' if data is None else 'insert' if id_col is None else 'edit')
                column_types = self.database_impl.get_column_types(self.get_db_resource(), table)
                for name, value in (data or {}).items():
                    expected = sobject.get_value(name, no_exception=True)
                    if isinstance(expected, (dict, list)):
                        expected = jsondumps(expected)
                    converted = self.database_impl.process_value(name, expected, column_types.get(name))
                    if converted:
                        expected = converted['value']
                    if value != expected and not (value == 'NULL' and expected is None):
                        raise UnsupportedContract('Workflow replay SQL must match its staged record: ' + name)
                object_write = True
            elif Container.get('Workflow:writing') and Container.get('Workflow:writing')[0] is sobject:
                from pyasm.command.workflow import _check_effect
                project = _check_effect(sobject, 'delete' if data is None else 'insert' if id_col is None else 'edit')
                owners = ('code', 'search_type', 'search_code', 'search_id', 'process', 'pipeline_code', 'message_code', 'login', 'project_code')
                if any(name in owners and value != sobject.get_value(name, no_exception=True) and
                       not (value == 'NULL' and sobject.get_value(name, no_exception=True) is None)
                       for name, value in (data or {}).items()):
                    raise UnsupportedContract('Workflow SQL must match its own staged effect')
                for name in data or ():
                    if not security.check_access('sobject_column', {'search_type': base, 'column': name, 'project': project}, 'edit'):
                        from pyasm.common.errors import SecurityException
                        raise SecurityException('Workflow effect column is not editable: ' + name)
                object_write = True
            elif (base in ('sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp') and data is not None
                  and self.get_db_resource()._get_connection_key() == system._get_connection_key()):
                object_write = True
            elif (base == 'sthpw/transaction_log' and data is None and
                  sobject.data.get('login') == self._context.login and sobject.data.get('type') == 'redo' and
                  self.get_db_resource()._get_connection_key() == system._get_connection_key()):
                object_write = True
            elif base == 'sthpw/sobject_list' and self.get_db_resource()._get_connection_key() == system._get_connection_key():
                from pyasm.security import Sudo
                if Sudo.is_sudo():
                    sobject._check_business_write('delete' if data is None else None)
                    object_write = True
            elif (base in ('sthpw/exception_log', 'sthpw/debug_log', 'sthpw/status_log', 'sthpw/retire_log') and data is not None and
                  self.get_db_resource()._get_connection_key() == system._get_connection_key()):
                sobject._check_business_write('insert' if id_col is None else 'edit')
                if (data.get('login') != self._context.login if id_col is None else set(data) != {'code'}):
                    raise UnsupportedContract('Internal log SQL must retain its authenticated author')
                object_write = True
        if not self.is_in_transaction() or not (object_write or
                (self.get_db_resource()._get_connection_key() == system._get_connection_key() and
                 table in self._system_write_tables())):
            raise UnsupportedContract('Native account writes require the system security transaction')
        if table == 'login' and (data is None or id_col is None):
            raise UnsupportedContract('Ordinary users cannot create or delete accounts')
        parameters, values = [], []
        for name, value in (data or {}).items():
            if name not in unquoted or value is None or isinstance(value, (bool, int, float, Decimal)):
                values.append(self.database_impl.get_parameter())
                parameters.append(value)
            elif value == 'NULL':
                values.append(self.database_impl.get_parameter())
                parameters.append(None)
            elif self._admin_sql:
                values.append(str(value))
            elif (isinstance(value, str) and
                  (self.database_impl.process_value(name, value, 'timestamp') == {'value': value, 'quoted': False} or
                   (table == 'login' and name == 'data' and value in (
                       self.database_impl.get_json_counter_update('data', 'invalid_logins'),
                       self.database_impl.get_json_counter_update('data', 'invalid_logins', True))))):
                # Closed native expressions; arbitrary unquoted SQL stays unsupported.
                values.append(value)
            else:
                raise UnsupportedContract('Unquoted account expression is not migrated')
        target = identifier(table)
        if data is None:
            if not object_write and ((table != 'ticket' and not (Container.get('Chat:writing') and table == 'subscription')) or id_col is None):
                raise UnsupportedContract('Ordinary users can only delete their own tickets')
            query = 'DELETE FROM ' + target
        elif id_col is None:
            if table == 'ticket' and data.get('login') != self._context.login:
                raise UnsupportedContract('Cannot create another user\'s ticket')
            query = 'INSERT INTO %s (%s) VALUES (%s)' % (
                target, ', '.join(identifier(name) for name in data), ', '.join(values))
            if insert_count > 1:
                query = 'INSERT INTO %s (%s) VALUES %s' % (
                    target, ', '.join(identifier(name) for name in data),
                    ', '.join(['(' + ', '.join(values) + ')'] * insert_count))
        else:
            query = 'UPDATE %s SET %s' % (target, ', '.join(
                '%s = %s' % (identifier(name), value) for name, value in zip(data, values)))
        if id_col is not None:
            query += ' WHERE %s = %s' % (identifier(id_col), self.database_impl.get_parameter())
            parameters.append(search_id)
            if table in ('login', 'ticket'):
                query += ' AND login = ' + self.database_impl.get_parameter()
                parameters.append(self._context.login)
            elif table == 'transaction_log' and data is None:
                query += ' AND login = %s AND type = %s' % ((self.database_impl.get_parameter(),) * 2)
                parameters.extend((self._context.login, 'redo'))
        return query, parameters, object_write

    def do_update_multiple(self, updates, sobjects, ignore_existing=False):
        """Bound native DML; authorize every row before opening its table scope."""
        if len(updates) != len(sobjects):
            raise ValueError('Each batch statement requires its own SObject')
        if not updates:
            return
        if any(update.table != updates[0].table for update in updates):
            raise UnsupportedContract('Batch statements require one table')
        if ignore_existing and any(not isinstance(update, Insert) or obj.get_id() != -1 or not obj.get_code()
                                   for update, obj in zip(updates, sobjects)):
            raise UnsupportedContract('Insert-if-absent requires new SObjects with a unique code')
        identity_column = ('file_name' if all(sobject.get_base_search_type() == 'sthpw/file' and
                           sobject.get_id() == -1 and not sobject.get_code() for sobject in sobjects) else 'code')
        statements = []
        for update, sobject in zip(updates, sobjects):
            inserting = isinstance(update, Insert)
            query, parameters, allowed = self._prepare_security_dml(
                update.table, update.data, None if inserting else sobject.get_id_col(),
                sobject.get_id(), update.unquoted_cols, sobject)
            if not allowed:
                raise UnsupportedContract('Batch writes require authenticated SObjects')
            statements.append((query, parameters))
        previous = getattr(self, '_sobject_write_table', None)
        inserted = {}
        try:
            self._sobject_write_table = updates[0].table
            position = 0
            while position < len(statements):
                first = position
                query = statements[position][0]
                parameters = []
                while position < len(statements) and statements[position][0] == query:
                    parameters.append(statements[position][1])
                    position += 1
                if isinstance(updates[first], Insert):
                    # Bound INSERT RETURNING supplies actual IDs without assuming row order or contiguous sequences.
                    # Stay below SQLite's older 999-parameter limit.
                    size = max(1, 900 // max(1, len(parameters[0])))
                    for offset in range(0, len(parameters), size):
                        portion = parameters[offset:offset + size]
                        update, sobject = updates[first], sobjects[first]
                        query, _, _ = self._prepare_security_dml(update.table, update.data,
                            unquoted=update.unquoted_cols, sobject=sobject, insert_count=len(portion))
                        conflict = ' ON CONFLICT (code) DO NOTHING' if ignore_existing else ''
                        result = self._do_update(query + conflict + ' RETURNING id, ' + identity_column,
                            parameters=[value for row in portion for value in row], security_write=True, returning=True,
                            native_table=self._native_metadata_table(update.table, update.data, update.unquoted_cols))
                        inserted.update((row[1], row[0]) for row in result)
                else:
                    update = updates[first]
                    self._do_update(query, parameters=parameters, security_write=True, multiple=True,
                                    native_table=self._native_metadata_table(update.table, update.data, update.unquoted_cols))
            return inserted
        finally:
            self._sobject_write_table = previous
            if self.vendor == 'Sqlite':
                self.conn.set_authorizer(self._authorize)

    def _do_update(self, query, quiet=False, parameters=None, security_write=False, multiple=False, returning=False, native_table=None):
        self._check_context()
        if self._read_depth:
            raise UnsupportedContract('Cannot write inside a read scope')
        if query == "":
            return
        if isinstance(query, (Insert, Update, Delete)):
            query = query.get_statement()
        if not isinstance(query, str):
            raise TypeError('Update must be SQL text, Insert, Update or Delete')
        if not query:
            return
        # Only known native DML without SQL triggers leaves routing/schema unchanged.
        invalidate_schema = not native_table or self.database_impl.has_table_triggers(self, native_table)
        invalidate_routing = invalidate_schema or native_table in ('search_object', 'project')
        if invalidate_schema:
            Container.clear_dict('DatabaseImpl:table_info')
            Container.clear_dict('SearchType:column_info')
        if invalidate_routing:
            Container.clear_dict('Store:resolve')
            Container.put('AccessManager:project_codes', None)
        if self.conn is None:
            self.connect()
        if not self._admin_sql and not ((Container.get('Security:writing') or Container.get('Chat:writing') or Container.get('UserProfile:writing') or getattr(self, '_sobject_write_table', None)) and
                                      (self.vendor == 'Sqlite' or security_write)):
            raise UnsupportedContract('Native SQL writes require administrator access')
        from pyasm.search.transaction import Transaction
        transaction = Transaction.get()
        if transaction and transaction.is_in_transaction():
            transaction.check_write_resource(self.get_db_resource())
            transaction.register_database(self)
            for other in transaction.get_databases().values():
                if (other is not self and getattr(other, '_has_writes', False) and
                        'PostgreSQL' in (self.vendor, other.vendor) and
                        not (transaction.can_write_resource(self.get_db_resource()) and
                             transaction.can_write_resource(other.get_db_resource()))):
                    raise UnsupportedContract('Coordinated PostgreSQL writes across databases are not migrated')
        # SQLite caches prepared statements: reauthorize at every write scope,
        # so a statement prepared during authentication cannot escape it.
        if self.vendor == 'Sqlite':
            self.conn.set_authorizer(self._authorize)
            if self.transaction_count and not self.conn.in_transaction:
                # sqlite3 starts implicit transactions for DML, but not ALTER/
                # CREATE TABLE or writable CTEs. They must join Command rollback.
                self.conn.execute('BEGIN IMMEDIATE')
        self.query = query
        try:
            self.cursor = self.conn.cursor()
            try:
                if multiple:
                    self.cursor.executemany(query, parameters)
                elif self.vendor == 'PostgreSQL':
                    # Extended protocol refuses multiple statements in one write.
                    self.cursor.execute(query, parameters, prepare=True)
                else:
                    self.cursor.execute(query, parameters or ())
                returned = self.cursor.fetchall() if returning else None
                self.row_count = self.cursor.rowcount
                self.last_row_id = self.cursor.lastrowid if self.vendor == 'Sqlite' else None
                self._has_writes = True
            finally:
                self.cursor.close()
            if self.transaction_count == 0:
                self.transaction_count = 1
                self.commit()
            if returning:
                return returned
        except self._errors as exc:
            if self.vendor == 'PostgreSQL' and self.transaction_count == 0:
                self.conn.rollback()
            raise SqlException(str(exc)) from exc
        finally:
            if invalidate_schema:
                Container.clear_dict('DatabaseImpl:table_info')
                Container.clear_dict('SearchType:column_info')
            if invalidate_routing:
                Container.clear_dict('Store:resolve')
                Container.put('AccessManager:project_codes', None)

    def set_savepoint(self, name="save_pt"):
        # Both PostgreSQL and SQLite emit real SAVEPOINT statements.
        if self.database_impl.has_savepoint():
            self._execute_savepoint(self.database_impl.set_savepoint(name))

    def rollback_savepoint(self, name="save_pt", release=True):
        if self.database_impl.has_savepoint():
            self._execute_savepoint(self.database_impl.rollback_savepoint(name))
            self.clear_table_cache()
            if release:
                self.release_savepoint(name)

    def release_savepoint(self, name="save_pt"):
        if self.database_impl.has_savepoint():
            self._execute_savepoint(self.database_impl.release_savepoint(name))

    def _execute_savepoint(self, statement):
        self._check_context()
        if self._read_depth or not self.transaction_count:
            raise UnsupportedContract('Savepoints require an active write transaction')
        if self.conn is None:
            self.connect()
        try:
            self.conn.execute(statement).close()
        except self._errors as exc:
            raise SqlException(str(exc)) from exc

    @staticmethod
    def _parameter_parts(statement, marker):
        # Markers inside SQL strings, identifiers, comments and dollar quotes are text.
        tokens = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\n]*|/\*[\s\S]*?\*/|"
                            r'\$(?P<tag>[A-Za-z_]\w*|)\$[\s\S]*?\$(?P=tag)\$|(?P<parameter>' + re.escape(marker) + ')')
        parts, start = [], 0
        for match in tokens.finditer(statement):
            if match.group('parameter'):
                parts.append(statement[start:match.start()])
                start = match.end()
        return parts + [statement[start:]]

    @staticmethod
    def _bound_query(statement, parameters, marker):
        parts = Sql._parameter_parts(statement, marker)
        if len(parts) != len(parameters) + 1:
            raise SqlException('Search parameter count does not match its filters')
        return marker.join(part.replace('%', '%%') for part in parts) if marker == '%s' else statement

    @staticmethod
    def quote(value, has_outside_quotes=True, escape=False, unicode_escape=False):
        if value is None:
            return "NULL"
        if isinstance(value, (list, tuple)):
            if not value:
                return "NULL"
            has_outside_quotes = False
            value = "(%s)" % ", ".join("'%s'" % item.replace("'", "''") for item in value)
        elif isinstance(value, str):
            value = value.replace("'", "''")
        else:
            # Original bool values enter the int branch and become True/False.
            value = str(value)
        if has_outside_quotes:
            return ("N'%s'" if unicode_escape else "'%s'") % value
        return "E'%s'" % value if escape else value


class _PostgresReadConnection:
    """Borrowed reads use native DECLARE cursors, never transaction-control SQL."""
    def __init__(self, sql):
        self._sql, self._cursors = sql, []

    def cursor(self):
        self._sql._check_context()
        if not self._sql._read_depth:
            raise UnsupportedContract('The borrowed read scope has ended')
        cursor = self._sql.conn.cursor(name='stream_cursor_' + uuid.uuid4().hex)
        self._cursors.append(cursor)
        return cursor

    def execute(self, query, parameters=None):
        from psycopg.rows import dict_row
        cursor = self.cursor()
        cursor.row_factory = dict_row
        return cursor.execute(query, parameters)

    def commit(self):
        raise UnsupportedContract('Cannot commit a borrowed read connection')

    def rollback(self):
        raise UnsupportedContract('Cannot roll back a borrowed read connection')

    def close(self):
        raise UnsupportedContract('Cannot close a borrowed read connection')

    def _close_cursors(self):
        for cursor in self._cursors:
            cursor.close()



class Delete:
    """Original Delete builder with its dangling AND and literal escaping fixed."""

    def __init__(self):
        self.impl = self.database = self.sql = None
        self.table = ''
        self.raw_filters = []

    def set_database(self, database):
        assert database == 'sthpw' or not isinstance(database, str)
        if isinstance(database, str):
            self.sql = DbContainer.get(database)
            self.db_resource = DbResource.get_default(database)
        elif DbResource.is_instance(database):
            self.sql = DbContainer.get(database)
            self.db_resource = database
            database = database.get_database()
        elif isinstance(database, Sql):
            self.sql = database
            self.db_resource = database.get_db_resource()
            database = database.get_database_name()
        else:
            raise TypeError('Statement connectors must be Sql or DbResource')
        self.database = database
        self.impl = self.sql.get_database_impl()

    def set_table(self, table):
        self.table = table

    def add_filter(self, name, value, op='='):
        if op not in ('=', '!=', '<>', '<', '<=', '>', '>=', 'LIKE', 'NOT LIKE', 'IS', 'IS NOT'):
            raise ValueError('Unsupported Delete operator: ' + str(op))
        self.raw_filters.append({'name': name, 'value': value, 'op': op})

    def get_statement(self):
        if self.sql is None:
            raise SqlException('No connector found to build Delete')
        if not self.raw_filters:
            # Source emitted invalid WHERE here; never turn an empty filter into a full wipe.
            raise ValueError('Delete requires at least one filter')
        schema = self.db_resource.get_schema()
        table = identifier(self.table)
        if schema and schema != 'public':
            table = identifier(schema) + '.' + table
        filters = []
        for item in self.raw_filters:
            value, op = item['value'], item['op']
            if value is None and op in ('=', '!=', '<>'):
                op = 'IS' if op == '=' else 'IS NOT'
            filters.append('%s %s %s' % (identifier(item['name']), op,
                                         'NULL' if value is None else Sql.quote(value)))
        return 'DELETE FROM %s WHERE %s' % (table, ' AND '.join(filters))


class CreateTable:
    """Original TACTIC table builder on native resource/transaction boundaries."""
    def __init__(self, search_type=None):
        from pyasm.biz import Project
        from pyasm.search import SearchType
        self.db_resource = (Project.get_db_resource_by_search_type(search_type)
                            if search_type else Project.get().get_project_db_resource())
        self.table = SearchType.get(search_type).get_table() if search_type else None
        self.impl = self.db_resource.get_database_impl()
        self.database = self.db_resource.get_database()
        self.columns, self.constraints, self.data = [], [], {}
        self.primary_key = None

    def set_table(self, table):
        self.table = table

    def get_table(self):
        return self.table

    def get_database(self):
        return self.db_resource.get_database()

    def add(self, name, type, length=None, not_null=False, primary_key=False):
        if type == "text":
            expr = self.impl.get_text(not_null=not_null)
        elif type == "char":
            expr = self.impl.get_char(length=length, not_null=not_null)
        elif type == "varchar":
            expr = self.impl.get_varchar(length=length, not_null=not_null)
        elif type == "int":
            expr = self.impl.get_int(not_null=not_null)
        elif type == "timestamp":
            expr = self.impl.get_timestamp(not_null=not_null)
        elif type == "boolean":
            expr = self.impl.get_boolean(not_null=not_null)
        elif type == "serial":
            expr = self.impl.get_serial(not_null=not_null)
        elif type in ["json", "jsonb"]:
            expr = self.impl.get_json(not_null=not_null)



        # SQL Server
        elif type == "uniqueidentifier":
            expr = self.impl.get_text(not_null=not_null)
        elif type in ["datetime", "datetime2"]:
            expr = self.impl.get_timestamp(not_null=not_null)
        elif type.startswith("datetimeoffset"):
            expr = self.impl.get_timestamp(not_null=not_null, timezone=True)
        elif type == "nvarchar":
            expr = self.impl.get_nvarchar(length=length, not_null=not_null)

        else:
            expr = type

        if not_null and not expr.upper().endswith(' NOT NULL'):
            expr += ' NOT NULL'
        self.impl.validate_data_type(expr)
        identifier(name)
        col_data = {
            'type': expr,
            'length': length,
            'not_null': not_null,
            'primary_key': primary_key
        }
        self.data[name] = col_data
        if primary_key:
            self.primary_key = name

    def add_column(self, name, type, length=None, not_null=False, primary_key=False):
        return self.add(name, type, length, not_null, primary_key=primary_key)

    def set_primary_key(self, name):
        if self.primary_key:
            raise TacticException("Primary key is already set")
        self.data[name]['primary_key'] = True
        self.primary_key = name

    def add_constraint(self, columns, mode="UNIQUE"):
        if isinstance(columns, str):
            columns = [columns]

        if mode not in ('UNIQUE', 'PRIMARY KEY'):
            raise ValueError('Unsupported table constraint')
        constraint = {
            'columns': columns,
            'mode': mode
        }
        self.constraints.append(constraint)

    def get_statement(self):
        schema = self.db_resource.get_schema()
        table = identifier(self.table)
        if schema and schema != 'public':
            table = identifier(schema) + '.' + table
        expressions = []
        for column, data in self.data.items():
            expr = data['type']
            if expr == 'timestamp':
                expr = self.impl.get_timestamp(default='now', not_null=data['not_null'])
            if data['primary_key']:
                expr += ' PRIMARY KEY'
                if self.impl.get_database_type() == 'Sqlite':
                    expr += ' AUTOINCREMENT'
            expressions.append('    %s %s' % (identifier(column), expr))
        for constraint in self.constraints:
            columns, mode = constraint['columns'], constraint['mode']
            if columns:
                name = '%s_%s_%s' % (self.table, '_'.join(columns), 'unique' if mode == 'UNIQUE' else 'idx')
                expressions.append('    CONSTRAINT %s %s (%s)' %
                                   (identifier(name), mode, ', '.join(identifier(c) for c in columns)))
        return 'CREATE TABLE %s (\n%s\n);\n' % (table, ',\n'.join(expressions))

    def commit(self, sql=None):
        sql = sql or DbContainer.get(self.db_resource)
        sql.check_schema_write()
        if not sql.get_database_impl().table_exists(sql.get_db_resource(), self.table):
            sql.do_update(self.get_statement())
            sql.clear_table_cache(sql.get_database_name())


class DropTable(Base):
    """Original drop/schema-cache contract on the active native transaction."""
    def __init__(self, search_type=None):
        from pyasm.biz import Project
        from pyasm.search import SearchType
        self.search_type = search_type
        self.db_resource = Project.get_db_resource_by_search_type(search_type)
        self.database = self.db_resource.get_database()
        self.table = SearchType.get(search_type).get_table()
        self.statement = self.get_statement()

    def get_statement(self):
        schema = self.db_resource.get_schema()
        table = identifier(self.table)
        if schema and schema != 'public':
            table = identifier(schema) + '.' + table
        return 'DROP TABLE ' + table

    def commit(self):
        from pathlib import Path
        from urllib.parse import quote
        from pyasm.common import Environment
        from pyasm.search import FileUndo, TableSchemaDumper, TableDropUndo
        sql = DbContainer.get(self.db_resource)
        sql.check_schema_write()
        if not sql.get_database_impl().table_exists(self.db_resource, self.table):
            return
        sql.get_database_impl().lock_table_for_drop(sql, self.table)
        # Preserve the original cache name for ordinary identifiers; encode path separators.
        schema_path = Path(Environment.get_tmp_dir()) / 'cache' / (
            'drop_%s_%s.sql' % (quote(self.database, safe=''), quote(self.table, safe='')))
        if schema_path.exists():
            FileUndo.remove(str(schema_path))
        TableSchemaDumper(self.search_type).dump_to_tactic(path=str(schema_path))
        TableDropUndo.log(self.search_type, self.database, self.table)
        sql.do_update(self.statement)
        sql.clear_table_cache()
        from pyasm.search import SObject, SearchType
        SObject.get_cache_dict(search_type=SearchType.get(self.search_type).get_base_key()).clear()


class Insert:
    def __init__(self):
        from pyasm.search.database_impl import DatabaseImpl
        self.table = self.sql = self.database = None
        self.data, self.column_types = {}, {}
        self.unquoted_cols, self.escape_quoted_cols = [], []
        self.impl, self.schema = DatabaseImpl.get(), ""

    def __str__(self):
        return self.get_statement()

    def set_database(self, database):
        assert database == "sthpw" or not isinstance(database, str)
        if isinstance(database, str):
            self.sql = DbContainer.get(database)
            self.db_resource = DbResource.get_default(database)
        elif DbResource.is_instance(database):
            self.sql = DbContainer.get(database)
            self.db_resource = database
        elif isinstance(database, Sql):
            self.sql = database
            self.db_resource = database.get_db_resource()
        else:
            raise UnsupportedContract("Statement connectors must be Sql or DbResource")
        self.impl = self.sql.get_database_impl()
        self.database = None  # Original SQLite omits database/schema qualification.

    def set_table(self, table):
        self.table = table

    def set_value(self, column, value, quoted=True, column_type="", escape_quoted=False):
        if value is None:
            value, quoted = "NULL", False
        if not column_type and self.sql:
            column_type = self.impl.get_column_types(self.db_resource, self.table).get(column)
            info = self.impl.process_value(column, value, column_type)
            if info:
                value, quoted = info.get("value"), info.get("quoted")
        self.data[column] = value
        # Lists intentionally retain a previous unquoted/escape flag on overwrite.
        if escape_quoted == True:
            self.escape_quoted_cols.append(column)
        elif not quoted:
            self.unquoted_cols.append(column)

    def get_data(self):
        return self.data

    def get_statement(self):
        from pyasm.search.storage import identifier
        self.impl.preprocess_sql(self.data, self.unquoted_cols)
        columns = sorted(self.data)
        values = []
        for column in columns:
            value = self.data[column]
            if column in self.unquoted_cols:
                value = str(value)
            elif column in self.escape_quoted_cols:
                value = Sql.quote(value, has_outside_quotes=False, escape=True)
            else:
                value = Sql.quote(value)
            values.append(value)
        statement = 'INSERT INTO %s (%s) VALUES (%s)' % (
            identifier(self.table), ", ".join(identifier(column) for column in columns), ", ".join(values))
        return self.impl.postprocess_sql(statement)

    def execute(self, sql=None):
        sql = sql or self.sql
        if sql is None:
            raise SqlException('No connector found to execute query')
        return sql.do_update(self.get_statement())

    def get_id_statement(self):
        if self.impl.get_database_type() == 'Sqlite':
            return 'SELECT last_insert_rowid()'
        sequence = self.impl.get_sequence_name(self.table)
        return self.impl.get_currval_select(sequence, getattr(self, 'db_resource', None))


class Update:
    def __init__(self):
        from pyasm.search.database_impl import DatabaseImpl
        self.table = self.sql = self.database = None
        self.data, self.column_types, self.filters = {}, {}, {}
        self.unquoted_cols, self.escape_quoted_cols = [], []
        self.raw_filters, self.wheres = [], []
        self.impl, self.schema = DatabaseImpl.get(), ""

    def __str__(self):
        return self.get_statement()

    def set_database(self, database):
        assert database == "sthpw" or not isinstance(database, str)
        if isinstance(database, str):
            self.sql = DbContainer.get(database)
            self.db_resource = DbResource.get_default(database)
        elif DbResource.is_instance(database):
            self.sql = DbContainer.get(database)
            self.db_resource = database
        elif isinstance(database, Sql):
            self.sql = database
            self.db_resource = database.get_db_resource()
        else:
            raise UnsupportedContract("Statement connectors must be Sql or DbResource")
        self.impl = self.sql.get_database_impl()
        self.database = None

    def set_table(self, table):
        self.table = table

    def set_value(self, column, value, quoted=True, column_type="", escape_quoted=False):
        if value is None:
            value, quoted = "NULL", False
        if isinstance(value, bytes):
            value = value.decode()
        if not column_type and self.sql:
            column_type = self.impl.get_column_types(self.db_resource, self.table).get(column)
            info = self.impl.process_value(column, value, column_type)
            if info:
                value, quoted = info.get("value"), info.get("quoted")
        self.data[column] = value
        if escape_quoted == True:
            self.escape_quoted_cols.append(column)
        elif quoted == False:
            self.unquoted_cols.append(column)

    def get_data(self):
        return self.data

    def add_where(self, where):
        if where != "":
            self.filters[where] = where

    def remove_filter(self, name):
        if self.filters.get(name):
            self.filters.pop(name)

    def add_filter(self, column, value, column_type="", table="", quoted=None):
        from pyasm.search.storage import identifier
        assert self.table
        self.raw_filters.append({"column": column, "value": value, "column_type": column_type, "quoted": quoted})
        subcolumn = None
        if "->>" in column or "->" in column:
            column, subcolumn = column.split("->>" if "->>" in column else "->")[:2]
        if not column_type and self.sql:
            column_type = self.impl.get_column_types(self.db_resource, self.table).get(column)
            info = self.impl.process_value(column, value, column_type)
            if info:
                value, quoted = info.get("value"), info.get("quoted")
        else:
            quoted = True
        if quoted is None:
            value = Sql.quote(value)
        name = (identifier(table) + '.' if table else "") + identifier(column)
        if subcolumn:
            name += '->>' + Sql.quote(subcolumn)
        self.add_where("%s = %s" % (name, value))

    def get_statement(self):
        from pyasm.search.storage import identifier
        self.impl.preprocess_sql(self.data, self.unquoted_cols)
        # The source requires set_database even when the update is empty.
        self.db_resource.get_database()
        pairs = []
        for column, value in self.data.items():
            if column in self.unquoted_cols:
                pass
            elif column in self.escape_quoted_cols:
                value = Sql.quote(value, has_outside_quotes=False, escape=True)
            else:
                value = Sql.quote(value)
            pairs.append('%s = %s' % (identifier(column), value))
        if not pairs:
            return ""
        statement = 'UPDATE %s SET %s' % (identifier(self.table), ", ".join(pairs))
        if self.filters:
            self.wheres = self.filters.values()
            statement += " WHERE %s" % " AND ".join(self.wheres)
        return self.impl.postprocess_sql(statement)

    def execute(self, sql=None):
        sql = sql or self.sql
        if sql is None:
            raise SqlException('No connector found to execute query')
        return sql.do_update(self.get_statement())

    def get_id_statement(self):
        select = Select()
        if self.sql is not None:
            select.set_database(self.sql)
        select.add_table(self.table)
        select.add_column('id')
        if self.filters:
            self.wheres = self.filters.values()
            for where in self.wheres:
                select.add_where(where)
        return select.get_statement()


class DbContainer(Base):
    @classmethod
    def close_thread_sql(cls):
        for sql in (Container.get("DbContainer::thread_pool") or {}).values():
            sql.close()
        Container.put("DbContainer::thread_pool", {})

    @staticmethod
    def register_connection(sql):
        from pyasm.search.transaction import Transaction
        transaction = Transaction.get()
        if transaction and transaction.is_in_transaction():
            transaction.register_database(sql)

    @classmethod
    def get(cls, db_resource, connect=True):
        assert db_resource is not None
        if db_resource == "sthpw":
            db_resource = DbResource.get_default("sthpw")
        else:
            assert DbResource.is_instance(db_resource)
        sql = cls.get_connection_pool_sql(db_resource)
        if sql.get_connection() is not None:
            cls.register_connection(sql)
        return sql

    @classmethod
    def get_connection_pool_sql(cls, db_resource):
        pool = Container.get("DbContainer::thread_pool")
        if pool is None:
            pool = {}
            Container.put("DbContainer::thread_pool", pool)
        # Same endpoint under different PostgreSQL credentials is a different connection.
        key = db_resource._get_connection_key()
        sql = pool.get(key)
        if sql is None:
            sql = Sql(db_resource)
            sql.connect()
            pool[key] = sql
        return sql

    @staticmethod
    def _get_sql_dict():
        return Container.get_full_dict("DbContainer:sql_dict")

    @staticmethod
    def rollback_all():
        for sql in Container.get_seq("DbContainer:sql_seq"):
            sql.rollback(force=True)

    @staticmethod
    def close_all():
        for sql in Container.get_seq("DbContainer:sql_seq"):
            sql.close()
        Container.put("DbContainer:sql_seq", [])
        Container.put("DbContainer:sql_dict", {})
        Container.put("DbContainer::thread_pool", {})
