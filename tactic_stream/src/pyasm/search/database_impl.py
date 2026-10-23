# Copyright (c) 2005, Southpaw Technology. See LICENSE.TACTIC.
"""Selected native SQLite/PostgreSQL dialects; see LICENSE.TACTIC/source_manifest.json."""
import re
from datetime import datetime
import json
from decimal import Decimal

from pyasm.common.common import Container, TacticException
from pyasm.common.errors import UnsupportedContract
from pyasm.common.common_exception import SetupException


class DatabaseImplException(TacticException):
    pass


class DatabaseImpl:
    def has_table_triggers(self, sql, table):
        return True

    @classmethod
    def get_text_search_filter(cls, column, keywords, column_type, table=None, op='&'):
        """default impl works with Postgres"""
        if isinstance(keywords, str):
    
            def split_keywords(keywords):
                keywords = keywords.strip()
                keywords = keywords.replace('  ', '')
                parts = keywords.split(' ')
                op_str = ' %s ' % op
                value = op_str.join(parts)
                return value
            if keywords.find('|') != -1 or keywords.find('&') != -1:
                keywords = re.sub('\\|+', '|', keywords)
                keywords = re.sub('\\&+', '&', keywords)
                keywords = keywords.rstrip('&')
                value = keywords
                if keywords.find('|') == -1 and keywords.find('&') == -1:
                    value = split_keywords(keywords)
            else:
                value = split_keywords(keywords)
        elif isinstance(keywords, list):
            keywords = filter(None, keywords)
            value = ' & '.join(keywords)
        else:
            value = str(keywords)
        config = 'english'
        value = value.replace("'", "''")
        if table:
            column = '"%s"."%s"' % (table, column)
        else:
            column = '"%s"' % column
        if column_type in ['integer', 'serial']:
            column = 'CAST(%s AS varchar(10))' % column
        else:
            value = '%s:*' % value
        wheres = []
        if column_type == 'tsvector':
            wheres.append(column)
        else:
            wheres.append("to_tsvector('%s', %s)" % (config, column))
        wheres.append('@@')
        wheres.append("to_tsquery('%s', '%s')" % (config, value))
        where = ' '.join(wheres)
        return where

    @staticmethod
    def get_datetime_filter(column, value, expression=False):
        return column, value

    def get_timestamp_filter(self, value):
        if isinstance(value, str) and value.upper() in ('NOW', 'CURRENT_TIMESTAMP'):
            return self.get_timestamp_now()
        return None

    def copy_table_schema(self, sql, from_table, to_table):
        raise UnsupportedContract("Template table copying is not migrated for this vendor")

    def lock_collection_table(self, sql, table, timeout=None):
        raise UnsupportedContract('Collection write locking is not migrated for this vendor')

    def get_child_codes_cte(self, collection_type, search_type, parent_collection_code):
        from pyasm.search import SearchType
        from pyasm.search.storage import identifier
        collection_table = identifier(SearchType.get(collection_type).get_table())
        table = identifier(SearchType.get(search_type).get_table())
        code = "'" + str(parent_collection_code).replace("'", "''") + "'"
        # UNION visits each code once, including diamonds and existing cycles.
        # Only the final reachable codes are needed; PostgreSQL ARRAY/depth is not.
        return '''WITH RECURSIVE res(search_code) AS (
            SELECT r.search_code FROM %s r JOIN %s p ON p.code=r.parent_code
            JOIN %s c ON c.code=r.search_code WHERE p.code=%s
            UNION
            SELECT r.search_code FROM %s r JOIN res ON r.parent_code=res.search_code
            JOIN %s c ON c.code=r.search_code
        ) SELECT search_code FROM res''' % (collection_table, table, table, code, collection_table, table)

    def snapshot_table(self, sql, table, data=True):
        import base64
        from pyasm.search.storage import identifier
        sql.check_schema_write()
        self.lock_table_for_drop(sql, table)
        snapshot = self.get_table_definition(sql, table)
        snapshot['vendor'] = sql.get_db_resource().get_vendor()
        snapshot['sequence'] = self.get_table_sequence_value(sql, table) if snapshot.get('sequence_name') else 0
        snapshot['rows'] = []
        if data:
            # ponytail: whole-table journal in memory; streamed backups if large DDL undo becomes common.
            names = [column['name'] for column in snapshot['columns']]
            for row in sql.do_query('SELECT %s FROM %s' % (','.join(map(identifier, names)), identifier(table))):
                values = []
                for column, value in zip(snapshot['columns'], row):
                    if isinstance(value, (bytes, memoryview)):
                        value = {'binary': base64.b64encode(bytes(value)).decode('ascii')}
                    elif column.get('json') and value is not None and snapshot['vendor'] == 'PostgreSQL':
                        value = json.dumps(value)
                    elif value is not None and not isinstance(value, (str, int, float, bool)):
                        value = str(value)
                    values.append(value)
                snapshot['rows'].append(values)
        return snapshot

    def restore_table(self, sql, table, snapshot):
        import base64
        from pyasm.search.storage import identifier
        sql.check_schema_write()
        if snapshot['vendor'] != sql.get_db_resource().get_vendor() or snapshot['table'] != table:
            raise ValueError('Schema backup does not match its resource')
        sql.clear_table_cache(sql.get_database_name())
        if self.table_exists(sql.get_db_resource(), table):
            raise DatabaseImplException('Cannot restore over an existing table: ' + table)
        sql.do_update(snapshot['statement'])
        names = [column['name'] for column in snapshot['columns']]
        if set(sql.get_column_info(table, use_cache=False)) != set(names):
            raise ValueError('Restored table columns do not match the backup')
        overriding = ' OVERRIDING SYSTEM VALUE' if snapshot.get('identity') == 'a' else ''
        for row in snapshot['rows']:
            columns = list(row) if isinstance(row, dict) else names
            if not set(columns).issubset(names) or (not isinstance(row, dict) and len(row) != len(names)):
                raise ValueError('Invalid schema backup row')
            values = [row[name] for name in columns] if isinstance(row, dict) else row
            values = [base64.b64decode(value['binary'], validate=True) if isinstance(value, dict) else value for value in values]
            insert = 'INSERT INTO %s (%s)%s VALUES (%s)' % (
                identifier(table), ','.join(map(identifier, columns)), overriding,
                ','.join([self.get_parameter()] * len(columns)))
            sql._do_update(insert, parameters=values)
        for statement in snapshot['extras']:
            sql.do_update(statement)
        if snapshot.get('sequence_name'):
            self.ensure_table_sequence(sql, table, snapshot['sequence'])
        sql.clear_table_cache(sql.get_database_name())

    def get_temp_column_name(self):
        # Only the original SQLServerImpl overrides this temporary column.
        return ""

    def get_table_sequence_value(self, sql, table):
        raise UnsupportedContract('Reading a table sequence is not migrated for this vendor')

    def lock_table_for_drop(self, sql, table, timeout=None):
        raise UnsupportedContract('Table drop locking is not migrated for this vendor')

    def upgrade_project_config(self, resource):
        from importlib.resources import files
        from pyasm.search import DbContainer
        sql = DbContainer.get(resource)
        sql.check_schema_write()
        upgrade = json.loads((files('tactic_stream') / 'compatibility/config_upgrade.json').read_text(encoding='utf-8'))
        for table, statement in upgrade['tables'].items():
            if not self.table_exists(resource, table):
                sql.do_update(self._bootstrap_statement(statement) if resource.get_vendor() == 'PostgreSQL' else statement)
        for migration in upgrade['columns']:
            if migration['column'] not in sql.get_column_info(migration['table'], use_cache=False):
                sql.do_update(migration['sql'])
        for migration in upgrade['drop_constraints']:
            self._drop_config_constraint(sql, migration['table'], migration['constraint'])
        if resource.get_vendor() == 'PostgreSQL':
            from pyasm.search.storage import identifier
            for migration in upgrade.get('text_columns', []):
                table, column = migration['table'], migration['column']
                info = sql.get_column_info(table, column, use_cache=False)
                if info and info['data_type'] != 'text':
                    sql.do_update('ALTER TABLE %s ALTER COLUMN %s TYPE text' % (identifier(table), identifier(column)))
        sql.clear_table_cache(resource.get_database())

    def ensure_table_sequence(self, sql, table, minimum=0):
        if not self.has_sequences():
            return
        from pyasm.search.storage import identifier
        sql.check_schema_write()
        sequence = self.get_sequence_name(table)
        last, called = sql.do_query('SELECT last_value, is_called FROM ' + identifier(sequence))[0]
        maximum = sql.get_value('SELECT MAX(id) FROM ' + identifier(table)) or 0
        target = max(int(maximum), int(minimum), int(last) if called else int(last) - 1) + 1
        # ALTER RESTART is transactional on PostgreSQL; setval is not. An import
        # failure must not leave a sequence reset behind or reuse an existing ID.
        sql.do_update('ALTER SEQUENCE %s RESTART WITH %d' % (identifier(sequence), target))

    @staticmethod
    def _creation_resource(database):
        from pyasm.search.sql import DbResource
        from pyasm.search.transaction import Transaction
        from pyasm.security.security import _require_admin
        _require_admin()
        transaction = Transaction.get()
        if transaction is None or not transaction.is_in_transaction():
            raise UnsupportedContract('Database creation requires an active Command/Transaction')
        resource = database if DbResource.is_instance(database) else DbResource.get_default(database)
        # Creation uses the configured endpoint; external project resources are
        # a separate migration. Never infer ownership from database existence.
        default = DbResource.get_default(resource.get_database())
        if resource._get_connection_key() != default._get_connection_key():
            raise UnsupportedContract('Creating databases on external resources is not migrated')
        return resource, transaction

    def import_schema(self, db_resource, type):
        from importlib.resources import files
        from pyasm.search.sql import DbContainer
        from pyasm.search.storage import Store
        resource, transaction = self._creation_resource(db_resource)
        if resource._get_connection_key() not in transaction.created_databases:
            raise UnsupportedContract('Schema import requires an exclusively new database')
        if type != 'simple':
            raise UnsupportedContract('Project base schema is not migrated: %s' % type)
        sql = DbContainer.get(resource)
        tables = json.loads((files('tactic_stream') / 'compatibility/project_schema.json').read_text(encoding='utf-8'))
        for statement in tables.values():
            sql.do_update(self._bootstrap_statement(statement) if resource.get_vendor() == 'PostgreSQL' else statement)
        # Apply the already adopted backend migrations, without spawning an
        # upgrade subprocess or committing the outer Command.
        for migration in Store._get_upgrade()['columns']:
            if migration['table'] in tables and migration['column'] not in sql.get_column_info(migration['table'], use_cache=False):
                sql.do_update(migration['sql'])
                if migration.get('after_add_sql'):
                    sql.do_update(migration['after_add_sql'])
        self.upgrade_project_config(resource)
        sql.clear_table_cache(resource.get_database())

    def import_default_data(self, db_resource, type):
        # The original simple_data.sql contains no INSERTs.
        if type != 'simple':
            raise UnsupportedContract('Default project data is not migrated: %s' % type)

    def table_exists(self, db_resource, table):
        return table in self.get_table_info(db_resource)

    @staticmethod
    def get(vendor=None):
        if vendor in (None, ''):
            from pyasm.common.config import Config
            vendor = Config.get_value('database', 'vendor', default='Sqlite')
        if isinstance(vendor, str) and vendor.lower() == 'sqlite':
            return SqliteImpl()
        if vendor == 'PostgreSQL':
            return PostgresImpl()
        raise UnsupportedContract("Database implementation is not migrated: %s" % vendor)

    @staticmethod
    def validate_data_type(value):
        import re
        # SQL types are grammar, never arbitrary SQL supplied by a client.
        pattern = (r'(?:text|varchar|character varying|char|character|integer|int[248]?|smallint|bigint|serial|bigserial|'
                   r'float[48]?|real|double precision|numeric|decimal|boolean|jsonb?|date|time|timestamp|bytea|blob|uuid)'
                   r'(?:\(\s*\d+\s*(?:,\s*\d+\s*)?\))?'
                   r'(?: with(?:out)? time zone)?(?:\[\])?(?: DEFAULT (?:NOW\(\)|CURRENT_TIMESTAMP))?(?: NOT NULL)?')
        if not isinstance(value, str) or not re.fullmatch(pattern, value, re.I):
            raise ValueError('Invalid or unsupported column type')

    def preprocess_sql(self, data, unquoted_cols):
        pass

    def postprocess_sql(self, statement):
        return statement

    def get_json_counter_update(self, column, key, reset=False):
        raise UnsupportedContract('Atomic JSON counters are not migrated for this database')


    def get_boolean(self, not_null=False):
        parts = []
        parts.append("boolean")
        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_serial(self, length=4, not_null=False):
        parts = []
        parts.append("serial")
        return " ".join(parts)

    def get_int(self, length=4, not_null=False):
        parts = []
        parts.append("int%s" % length)
        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_text(self, not_null=False):
        parts = []
        parts.append("text")
        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_char(self, length=256, not_null=False):
        assert length
        parts = []
        parts.append("char(%s)" % length)
        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_varchar(self, length=256, not_null=False):
        if not length:
            length = 256

        if length in [-1, 'max']:
            return self.get_text(not_null=not_null)
        parts = []
        parts.append("varchar(%s)" % length)
        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_nvarchar(self, length=256, not_null=False):
        return self.get_varchar(length=length, not_null=not_null)

    def get_timestamp(self, default=None, not_null=False, timezone=False):
        parts = []
        if timezone:
            parts.append("timestamp with time zone")
        else:
            parts.append("timestamp")
        if default:
            if default == "now":
                parts.append("DEFAULT %s" % self.get_timestamp_now())
            else:
                parts.append("DEFAULT %s" % default)

        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_json(self, not_null=False):
       parts = []
       parts.append("jsonb")
       if not_null:
           parts.append("NOT NULL")
       return " ".join(parts)

class SqliteImpl(DatabaseImpl):
    def has_table_triggers(self, sql, table):
        return bool(sql.do_query("SELECT 1 FROM sqlite_master WHERE type='trigger' AND tbl_name=%s "
                                 "UNION ALL SELECT 1 FROM sqlite_temp_master WHERE type='trigger' AND tbl_name=%s" %
                                 (sql.quote(table), sql.quote(table))))

    def get_page(self, limit=None, offset=0, table_input=0, already_in_where_clause=0):
        if limit is None:
            return 'LIMIT -1 OFFSET %d' % int(offset) if offset else None
        return 'LIMIT %d%s' % (int(limit), ' OFFSET %d' % int(offset) if offset else '')

    @classmethod
    def get_text_search_filter(cls, column, keywords, column_type, table=None, op='&'):
        raise UnsupportedContract('Native full-text Select filters require PostgreSQL')

    @staticmethod
    def utc_timestamp(value):
        from datetime import timezone
        if value is None or value == '':
            return value
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')

    @classmethod
    def get_datetime_filter(cls, column, value, expression=False):
        return 'spt_timestamp(%s)' % column, ('spt_timestamp(%s)' % value if expression else cls.utc_timestamp(value))

    def get_timestamp_filter(self, value):
        expression = super().get_timestamp_filter(value)
        if expression is not None or not isinstance(value, str):
            return expression
        literal = r"(?:'(?:[^']|'')*'|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?|NULL)"
        if re.fullmatch(r'DATETIME\(\s*(?:' + literal + r'(?:\s*,\s*' + literal + r')*)?\s*\)', value, re.I):
            return value
        if value.upper().startswith(('CURRENT_TIMESTAMP', 'DATETIME(')):
            raise ValueError('Invalid timestamp expression')
        return None

    @staticmethod
    def configure_connection(connection):
        # Server scripts use PostgreSQL expressions on both supported vendors.
        import re

        def regex_match(value, pattern, insensitive):
            if value is None or pattern is None:
                return None
            return bool(re.search(pattern, str(value), re.I if insensitive else 0))

        def split_part(value, delimiter, field):
            if value is None or delimiter is None or field is None:
                return None
            if field == 0:
                raise ValueError('split_part field must not be zero')
            parts = str(value).split(delimiter) if delimiter else [str(value)]
            index = field - 1 if field > 0 else field
            return parts[index] if -len(parts) <= index < len(parts) else ''

        connection.create_function('spt_regex', 3, regex_match, deterministic=True)
        connection.create_function('split_part', 3, split_part, deterministic=True)
        connection.create_function('spt_timestamp', 1, SqliteImpl.utc_timestamp, deterministic=True)

    def lock_collection_table(self, sql, table, timeout=None):
        sql._check_context()
        if not sql.transaction_count or sql._read_depth:
            raise UnsupportedContract('Collection writes require a write transaction')
        if sql.conn is None:
            sql.connect()
        if not sql.conn.in_transaction:
            previous = sql.conn.execute('PRAGMA busy_timeout').fetchone()[0] if timeout is not None else None
            try:
                if timeout is not None:
                    sql.conn.execute('PRAGMA busy_timeout=%d' % int(timeout))
                sql.conn.execute('BEGIN IMMEDIATE')
            finally:
                if previous is not None:
                    sql.conn.execute('PRAGMA busy_timeout=%d' % previous)

    def copy_table_schema(self, sql, from_table, to_table):
        import re
        import sqlite3
        from contextlib import closing
        from pyasm.search.storage import identifier
        definition = self.get_table_definition(sql, from_table)
        if sql.do_query('PRAGMA foreign_key_list(%s)' % identifier(from_table)):
            raise UnsupportedContract('Template foreign constraints require schema migration')
        if sql.do_query("SELECT 1 FROM sqlite_master WHERE type='trigger' AND tbl_name=" + sql.quote(from_table)):
            raise UnsupportedContract('Template SQL triggers require schema migration')
        # Let SQLite rewrite table references; never replace names inside literals/columns.
        with closing(sqlite3.connect(':memory:')) as clone:
            clone.execute(definition['statement'])
            for statement in definition['extras']:
                clone.execute(statement)
            clone.execute('ALTER TABLE %s RENAME TO %s' % (identifier(from_table), identifier(to_table)))
            statement = clone.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (to_table,)).fetchone()[0]
            indexes = clone.execute("SELECT name,sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL ORDER BY name", (to_table,)).fetchall()
        statements = [statement]
        for name, statement in indexes:
            new_name = to_table + '_' + name
            replacement = lambda match: match[1] + ' ' + identifier(new_name)
            statement, count = re.subn(r'^(CREATE(?:\s+UNIQUE)?\s+INDEX)\s+(?:"[^"]+"|`[^`]+`|\[[^\]]+\]|\w+)', replacement, statement, count=1, flags=re.I)
            if count != 1:
                raise UnsupportedContract('Unsupported template index definition')
            if sql.do_query("SELECT 1 FROM sqlite_master WHERE name=" + sql.quote(new_name)):
                raise DatabaseImplException('Template index name already exists: ' + new_name)
            statements.append(statement)
        for statement in statements:
            sql.do_update(statement)

    def get_table_definition(self, sql, table):
        from pyasm.search.storage import identifier
        definition = sql.get_value("SELECT sql FROM sqlite_master WHERE type='table' AND name=" + sql.quote(table))
        if not definition or definition.lstrip().upper().startswith('CREATE VIRTUAL'):
            raise UnsupportedContract('Only ordinary tables support schema replay')
        columns = sql.do_query('PRAGMA table_xinfo(%s)' % identifier(table))
        if any(column[6] for column in columns):
            raise UnsupportedContract('Generated columns do not support schema replay yet')
        return dict(table=table, statement=definition,
            columns=[dict(name=row[1], nullable=not bool(row[3]), default=row[4]) for row in columns],
            extras=[row[0] for row in sql.do_query("SELECT sql FROM sqlite_master WHERE tbl_name=%s "
                "AND type IN ('index','trigger') AND sql IS NOT NULL ORDER BY type,name" % sql.quote(table))],
            sequence_name=table if 'AUTOINCREMENT' in definition.upper() else '')

    def get_table_sequence_value(self, sql, table):
        from pyasm.search.storage import identifier
        from pyasm.search.sql import Sql
        maximum = int(sql.get_value('SELECT MAX(id) FROM ' + identifier(table)) or 0)
        if not sql.do_query("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"):
            return maximum
        last = sql.get_value('SELECT seq FROM sqlite_sequence WHERE name=' + Sql.quote(table)) or 0
        return max(maximum, int(last))

    def ensure_table_sequence(self, sql, table, minimum=0):
        if not minimum:
            return
        from pyasm.search.sql import Sql
        sql.check_schema_write()
        if self.get_table_sequence_value(sql, table) >= int(minimum):
            return
        definition = sql.get_value('SELECT sql FROM sqlite_master WHERE type=\'table\' AND name=' + Sql.quote(table))
        if 'AUTOINCREMENT' not in definition.upper():
            raise UnsupportedContract('A sequence floor requires an AUTOINCREMENT table')
        if sql.do_query('SELECT seq FROM sqlite_sequence WHERE name=' + Sql.quote(table)):
            sql.do_update('UPDATE sqlite_sequence SET seq=%d WHERE name=%s' % (int(minimum), Sql.quote(table)))
        else:
            sql.do_update('INSERT INTO sqlite_sequence(name,seq) VALUES(%s,%d)' % (Sql.quote(table), int(minimum)))

    def lock_table_for_drop(self, sql, table, timeout=None):
        import sqlite3
        from pyasm.search import SqlException
        from pyasm.search.storage import identifier
        sql.check_schema_write()
        self.lock_collection_table(sql, table, timeout=timeout)
        # SQLite permits dangling views after DROP; inspect actual compiled
        # reads (including nested views), rather than parse SQL with a regex.
        views = sql.do_query("SELECT name FROM sqlite_master WHERE type='view'")
        references = set()
        def authorize(action, name, column, database, source):
            if action == sqlite3.SQLITE_READ and name:
                references.add(name)
            return sql._authorize(action, name, column, database, source)
        for view, in views:
            sql.conn.set_authorizer(authorize)
            try:
                sql.conn.execute('EXPLAIN SELECT * FROM ' + identifier(view)).close()
            except sqlite3.Error as exception:
                raise SqlException('Cannot inspect dependent view: ' + view) from exception
            finally:
                sql.conn.set_authorizer(sql._authorize)
            if table in references:
                raise SqlException('Cannot drop table referenced by view: ' + view)
        for other, in sql.do_query("SELECT name FROM sqlite_master WHERE type='table'"):
            if any(row[2].casefold() == table.casefold() for row in sql.do_query('PRAGMA foreign_key_list(%s)' % identifier(other))):
                raise SqlException('Cannot drop table referenced by foreign key: ' + other)

    def get_constraints(self, db_resource, table):
        from pyasm.search import DbContainer, Sql
        from pyasm.search.storage import identifier
        db = DbContainer.get(db_resource)
        kind = db.get_value('SELECT type FROM sqlite_master WHERE name=' + Sql.quote(table))
        if kind == 'view':
            raise UnsupportedContract('SQL view export is not migrated')
        if db.do_query('PRAGMA foreign_key_list(%s)' % identifier(table)):
            raise UnsupportedContract('Foreign key export is not migrated')
        constraints = []
        primary = sorted((row[5], row[1]) for row in db.do_query('PRAGMA table_info(%s)' % identifier(table)) if row[5])
        if primary:
            constraints.append(dict(name=table + '_pkey', mode='PRIMARY KEY', columns=[name for _, name in primary]))
        for row in db.do_query('PRAGMA index_list(%s)' % identifier(table)):
            if not row[2] or row[3] == 'pk':
                continue
            columns = [column[2] for column in db.do_query('PRAGMA index_info(%s)' % identifier(row[1]))]
            if row[4] or None in columns:
                raise UnsupportedContract('Partial/expression unique indexes are not migrated')
            constraints.append(dict(name=row[1], mode='UNIQUE', columns=columns))
        return constraints

    def _drop_config_constraint(self, sql, table, constraint):
        from pyasm.search.storage import Store
        Store._drop_constraint(sql.get_connection(), table, constraint, sql.do_update)

    def database_exists(self, database, host=None):
        from pyasm.search.search import _context
        from pyasm.search.sql import DbResource
        if host not in (None, '', 'localhost'):
            raise UnsupportedContract('SQLite resources must be local')
        name = database.get_database() if DbResource.is_instance(database) else database
        return _context.get().store.database_path(name).exists()

    def create_database(self, database):
        from pyasm.search.search import _context
        resource, transaction = self._creation_resource(database)
        path = _context.get().store.database_path(resource.get_database())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=False)
        transaction.register_created_database(resource)

    def _drop_created_database(self, resource):
        from pyasm.search.search import _context
        _context.get().store.database_path(resource.get_database()).unlink()

    def table_exists(self, db_resource, table):
        from pyasm.search.sql import DbContainer
        sql = DbContainer.get(db_resource)
        return bool(sql.do_query("SELECT name FROM sqlite_master WHERE type='table' AND name=%s" % sql.quote(table)))

    def get_serial(self, length=4, not_null=False):
        parts = []
        parts.append("integer")
        return " ".join(parts)

    def get_timestamp(self, default='now', not_null=False):
        parts = []
        parts.append("timestamp")
        if default:
            if default == "now":
                parts.append("DEFAULT %s" % self.get_timestamp_now())
            else:
                parts.append("DEFAULT %s" % default)

        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_parameter(self):
        return '?'

    def get_bound_regex_filter(self, column, regex, op='EQI'):
        if op not in ('EQ', 'EQI', 'NEQ', 'NEQI'):
            raise UnsupportedContract('Unsupported SQLite regex operator: ' + op)
        return '%sspt_regex(%s, ?, %d)' % ('NOT ' if op.startswith('NEQ') else '', column, op.endswith('I')), str(regex or '')

    def get_json_counter_update(self, column, key, reset=False):
        from pyasm.search.storage import identifier
        import json
        name = identifier(column)
        path = ('$.' + json.dumps(key)).replace("'", "''")
        count = '0' if reset else "COALESCE(json_extract(%s, '%s'), 0) + 1" % (name, path)
        return "json_set(COALESCE(%s, '{}'), '%s', %s)" % (name, path, count)

    def get_database_type(self):
        return "Sqlite"

    def has_sequences(self):
        return False

    def has_savepoint(self):
        return True

    def set_savepoint(self, name='save_pt'):
        from pyasm.search.storage import identifier
        return 'SAVEPOINT %s' % identifier(name)

    def rollback_savepoint(self, name='save_pt', release=False):
        from pyasm.search.storage import identifier
        return 'ROLLBACK TO SAVEPOINT %s' % identifier(name)

    def release_savepoint(self, name='save_pt'):
        from pyasm.search.storage import identifier
        return 'RELEASE SAVEPOINT %s' % identifier(name)

    def get_timestamp_now(self, offset=None, type=None, op='+'):
        if not offset:
            return "CURRENT_TIMESTAMP"
        if op == '-':
            offset *= -1
        if not type:
            type = "days"
        elif type.lower() in ("week", "weeks"):
            type = "days"
            offset *= 7
        elif not type.endswith('s'):
            type += 's'
        return "DATETIME('now','%s %s')" % (offset, type)

    def process_value(self, name, value, column_type="varchar"):
        quoted = True
        if value == "NULL":
            quoted = False
        elif column_type == "boolean":
            value = 1 if value in ('true', 'True', 1, '1', True) else 0
            quoted = False
        elif column_type in ('timestamp', 'datetime', 'datetime2'):
            if value is None:
                return {'value': None, 'quoted': False}
            if not isinstance(value, (str, datetime)):
                raise TypeError('Expected timestamp string or datetime')
            expression = self.get_timestamp_filter(value)
            if expression is not None:
                value, quoted = expression, False
        elif column_type in ('json', 'jsonb') and isinstance(value, str) and value.startswith('json_set('):
            quoted = False
        return {"value": value, "quoted": quoted}

    @classmethod
    def get_column_info(cls, db_resource, table, use_cache=True):
        from pyasm.search.sql import DbContainer, Sql
        from pyasm.search.storage import identifier
        cache = Container.get("DatabaseImpl:column_info")
        if cache is None:
            cache = {}
            Container.put("DatabaseImpl:column_info", cache)
        resource = db_resource.get_db_resource() if isinstance(db_resource, Sql) else db_resource
        key = "%s:%s" % (resource, table)
        if use_cache and key in cache:
            return cache[key]
        result = {}
        cache[key] = result
        sql = db_resource if isinstance(db_resource, Sql) else DbContainer.get(db_resource)
        for row in sql.do_query("PRAGMA table_info(%s)" % identifier(table)):
            name, data_type, nullable = row[1], row[2], row[3] not in (1, 99)
            size = 0
            if data_type.startswith("character varying"):
                size = int(data_type.removeprefix("character varying").replace("(", "").replace(")", ""))
                data_type = "varchar"
            elif data_type.startswith("varchar"):
                size = data_type.removeprefix("varchar").replace("(", "").replace(")", "")
                size = int(size) if size else 256
                data_type = "varchar"
            elif data_type.startswith("timestamp"):
                data_type = "timestamp"
            result[name] = {"data_type": data_type, "nullable": nullable, "size": size}
        return result

    def get_column_types(self, database, table):
        return {name: info.get("data_type") for name, info in self.get_column_info(database, table).items()}


class PostgresImpl(DatabaseImpl):
    def has_table_triggers(self, sql, table):
        from pyasm.search.storage import identifier
        relation = identifier(sql.get_db_resource().get_schema() or 'public') + '.' + identifier(table)
        return bool(sql.do_query('SELECT 1 FROM pg_trigger WHERE tgrelid=to_regclass(%s) AND NOT tgisinternal' % sql.quote(relation)))

    def lock_collection_table(self, sql, table, timeout=None):
        from pyasm.search.storage import identifier
        sql._check_context()
        if not sql.transaction_count or sql._read_depth:
            raise UnsupportedContract('Collection writes require a write transaction')
        if sql.conn is None:
            sql.connect()
        # Serialize check+insert so parallel requests cannot add a duplicate/cycle.
        if timeout is not None:
            sql.conn.execute("SELECT set_config('lock_timeout', %s, true)", (str(int(timeout)) + 'ms',))
        sql.conn.execute('LOCK TABLE %s IN SHARE ROW EXCLUSIVE MODE' % identifier(table))

    def copy_table_schema(self, sql, from_table, to_table):
        from pyasm.search.storage import identifier
        definition = self.get_table_definition(sql, from_table)
        schema = sql.get_db_resource().get_schema() or 'public'
        source = identifier(schema) + '.' + identifier(from_table)
        target = identifier(schema) + '.' + identifier(to_table)
        if sql.do_query('SELECT 1 FROM pg_trigger WHERE tgrelid=to_regclass(%s) AND NOT tgisinternal' % sql.quote(source)):
            raise UnsupportedContract('Template SQL triggers require schema migration')
        sql.do_update('CREATE TABLE %s (LIKE %s INCLUDING ALL)' % (target, source))
        if definition['sequence_name'] and not definition['identity']:
            # LIKE copies a serial default pointing at the source sequence; give the copy its own.
            sequence = identifier(schema) + '.' + identifier(self.get_sequence_name(to_table))
            data_type = sql.get_column_info(from_table)['id']['data_type']
            sql.do_update('CREATE SEQUENCE %s AS %s' % (sequence, 'bigint' if data_type == 'bigint' else 'integer'))
            sql.do_update('ALTER TABLE %s ALTER COLUMN id SET DEFAULT nextval(%s::regclass)' % (target, sql.quote(sequence)))
            sql.do_update('ALTER SEQUENCE %s OWNED BY %s.id' % (sequence, target))

    def get_table_definition(self, sql, table):
        from pyasm.search.storage import identifier
        schema = sql.get_db_resource().get_schema() or 'public'
        relation = identifier(schema) + '.' + identifier(table)
        oid = sql.get_value('SELECT to_regclass(' + sql.quote(relation) + ')::oid')
        if not oid:
            raise DatabaseImplException('Table does not exist: ' + table)
        oid = int(oid)
        properties = sql.do_query('SELECT relkind,relpersistence,relrowsecurity,reloptions,reltablespace,relacl '
                                 'FROM pg_class WHERE oid=%d' % oid)[0]
        if properties != ('r', 'p', False, None, 0, None) or sql.do_query(
                'SELECT 1 FROM pg_inherits WHERE inhrelid=%d OR inhparent=%d' % (oid, oid)):
            raise UnsupportedContract('Special tables, inheritance, policies or explicit grants require schema migration')
        columns = sql.do_query('SELECT a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,'
            'pg_get_expr(d.adbin,d.adrelid),a.attidentity,a.attgenerated,t.typcategory,a.attcollation<>t.typcollation '
            'FROM pg_attribute a JOIN pg_type t ON t.oid=a.atttypid '
            'LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum '
            'WHERE a.attrelid=%d AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum' % oid)
        definitions, metadata = [], []
        sequence_name, identity = '', ''
        for name, data_type, not_null, default, identity_mode, generated, category, collation in columns:
            if generated or collation or category in ('A', 'C', 'E', 'R', 'M'):
                raise UnsupportedContract('Generated, array, custom and nondefault collation columns require schema migration')
            column = identifier(name) + ' ' + data_type
            if identity_mode or (default and 'nextval(' in default):
                if name != 'id':
                    raise UnsupportedContract('Only the standard SObject id sequence supports replay')
                sequence = sql.get_value('SELECT pg_get_serial_sequence(%s,%s)' % (sql.quote(relation), sql.quote(name)))
                expected = identifier(schema) + '.' + identifier(self.get_sequence_name(table))
                if not sequence or sql.get_value('SELECT to_regclass(%s)::oid=to_regclass(%s)::oid' %
                                                (sql.quote(sequence), sql.quote(expected))) is not True:
                    raise UnsupportedContract('Nonstandard SObject sequence requires schema migration')
                sequence_name, identity = self.get_sequence_name(table), identity_mode
                if identity_mode:
                    column += ' GENERATED %s AS IDENTITY' % ('ALWAYS' if identity_mode == 'a' else 'BY DEFAULT')
                else:
                    column = identifier(name) + (' bigserial' if data_type == 'bigint' else ' serial')
                sequence_options = sql.do_query('SELECT seqincrement,seqmin,seqstart,seqcache,seqcycle,seqmax FROM pg_sequence '
                    'WHERE seqrelid=to_regclass(%s)' % sql.quote(sequence))[0]
                if sequence_options != (1, 1, 1, 1, False, 2 ** (63 if data_type == 'bigint' else 31) - 1):
                    raise UnsupportedContract('Nonstandard sequence settings require schema migration')
            elif default is not None:
                column += ' DEFAULT ' + default
            if not_null:
                column += ' NOT NULL'
            definitions.append(column)
            metadata.append(dict(name=name, nullable=not not_null, default=default, json=data_type in ('json', 'jsonb')))
        constraints = sql.do_query('SELECT conname,contype,pg_get_constraintdef(oid) FROM pg_constraint '
                                  'WHERE conrelid=%d ORDER BY conname' % oid)
        for name, kind, definition in constraints:
            if kind not in ('p', 'u', 'c', 'n'):
                raise UnsupportedContract('Foreign and exclusion constraints require schema migration')
            if kind != 'n':
                definitions.append('CONSTRAINT %s %s' % (identifier(name), definition))
        if sql.do_query("SELECT 1 FROM pg_rewrite WHERE ev_class=%d AND rulename<>'_RETURN'" % oid):
            raise UnsupportedContract('Table rules require schema migration')
        if sql.do_query("SELECT 1 FROM pg_trigger WHERE tgrelid=%d AND NOT tgisinternal AND tgenabled<>'O'" % oid):
            raise UnsupportedContract('Disabled or replication triggers require schema migration')
        extras = [row[0] for row in sql.do_query('SELECT pg_get_indexdef(i.indexrelid) FROM pg_index i '
            'WHERE i.indrelid=%d AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid=i.indexrelid) '
            'ORDER BY i.indexrelid' % oid)]
        extras.extend(row[0] for row in sql.do_query('SELECT pg_get_triggerdef(oid) FROM pg_trigger '
                                                   'WHERE tgrelid=%d AND NOT tgisinternal ORDER BY tgname' % oid))
        return dict(table=table, statement='CREATE TABLE %s (%s)' % (relation, ','.join(definitions)),
                    columns=metadata, extras=extras, sequence_name=sequence_name, identity=identity)

    def get_table_sequence_value(self, sql, table):
        from pyasm.search.storage import identifier
        sequence = self.get_sequence_name(table)
        last, called = sql.do_query('SELECT last_value, is_called FROM ' + identifier(sequence))[0]
        maximum = int(sql.get_value('SELECT MAX(id) FROM ' + identifier(table)) or 0)
        return max(maximum, int(last) if called else int(last) - 1)

    def lock_table_for_drop(self, sql, table, timeout=None):
        from pyasm.search.storage import identifier
        sql.check_schema_write()
        if timeout is not None:
            if sql.conn is None:
                sql.connect()
            sql.conn.execute("SELECT set_config('lock_timeout', %s, true)", (str(int(timeout)) + 'ms',))
        schema = sql.get_db_resource().get_schema() or 'public'
        sql.do_update('LOCK TABLE %s.%s IN ACCESS EXCLUSIVE MODE' % (identifier(schema), identifier(table)))

    def get_constraints(self, db_resource, table):
        from pyasm.search import DbContainer, Sql
        db = DbContainer.get(db_resource)
        schema = db_resource.get_schema() or 'public'
        kind = db.get_value('SELECT c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace '
                            'WHERE n.nspname=%s AND c.relname=%s' % (Sql.quote(schema), Sql.quote(table)))
        if kind != 'r':
            raise UnsupportedContract('SQL view/partition export is not migrated')
        rows = db.do_query('SELECT con.conname, con.contype, a.attname FROM pg_constraint con '
            'JOIN pg_class c ON c.oid=con.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace '
            'LEFT JOIN LATERAL unnest(con.conkey) WITH ORDINALITY k(attnum, position) ON true '
            'LEFT JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=k.attnum '
            'WHERE n.nspname=%s AND c.relname=%s ORDER BY con.conname,k.position' % (Sql.quote(schema), Sql.quote(table)))
        constraints = {}
        for name, mode, column in rows:
            if mode in ('c', 'n'):
                continue  # NOT NULL is in column info; original dumps omit CHECK.
            if mode not in ('p', 'u'):
                raise UnsupportedContract('Foreign/exclusion constraints are not migrated')
            constraint = constraints.setdefault(name, dict(name=name, mode='PRIMARY KEY' if mode == 'p' else 'UNIQUE', columns=[]))
            constraint['columns'].append(column)
        rows = db.do_query('SELECT i.relname, a.attname, ix.indpred IS NOT NULL, ix.indexprs IS NOT NULL, '
            'ix.indnullsnotdistinct FROM pg_index ix JOIN pg_class c ON c.oid=ix.indrelid '
            'JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_class i ON i.oid=ix.indexrelid '
            'JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY k(attnum, position) ON k.position<=ix.indnkeyatts '
            'LEFT JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=k.attnum '
            'WHERE ix.indisunique AND NOT ix.indisprimary AND n.nspname=%s AND c.relname=%s '
            'ORDER BY i.relname,k.position' % (Sql.quote(schema), Sql.quote(table)))
        for name, column, partial, expression, nulls_equal in rows:
            if partial or expression or nulls_equal:
                raise UnsupportedContract('Partial/expression/NULLS NOT DISTINCT unique indexes are not migrated')
            if name not in constraints:
                constraints[name] = dict(name=name, mode='UNIQUE', columns=[])
            if column not in constraints[name]['columns']:
                constraints[name]['columns'].append(column)
        return list(constraints.values())

    def _drop_config_constraint(self, sql, table, constraint):
        from pyasm.search.storage import identifier
        sql.do_update('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %s' % (identifier(table), identifier(constraint)))

    REGEX_OPERATORS = {'EQI': '~*', 'EQ': '~', 'NEQI': '!~*', 'NEQ': '!~'}

    def database_exists(self, database, host=None, port=None):
        from pyasm.search.sql import DbResource
        resource = database if DbResource.is_instance(database) else DbResource.get_default(database)
        if host is not None or port is not None:
            raise UnsupportedContract('Use an explicit DbResource for remote database checks')
        with self._connect(resource, 'postgres', autocommit=True) as db:
            return bool(db.execute('SELECT 1 FROM pg_database WHERE datname=%s', (resource.get_database(),)).fetchone())

    def create_database(self, database):
        from psycopg import sql
        resource, transaction = self._creation_resource(database)
        with self._connect(resource, 'postgres', autocommit=True) as db:
            if db.execute('SELECT 1 FROM pg_database WHERE datname=%s', (resource.get_database(),)).fetchone():
                raise FileExistsError('PostgreSQL database already exists: ' + resource.get_database())
            db.execute(sql.SQL('CREATE DATABASE {} ENCODING \'UTF8\'').format(sql.Identifier(resource.get_database())))
            transaction.register_created_database(resource)

    def _drop_created_database(self, resource):
        from psycopg import sql
        with self._connect(resource, 'postgres', autocommit=True) as db:
            # No FORCE or session termination; only resources owned by the
            # current failed creation transaction reach this method.
            db.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(resource.get_database())))

    @staticmethod
    def _bootstrap_statement(statement):
        import re
        # Only the shipped, trusted DDL uses this conversion. Never user SQL.
        statement = statement.replace('integer PRIMARY KEY AUTOINCREMENT', 'serial PRIMARY KEY')
        return re.sub(r'\bjson\b', 'jsonb', statement)

    @staticmethod
    def _connect(resource, database=None, autocommit=False):
        """Installation and non-recursive identity checks use direct connections."""
        try:
            import psycopg
        except ImportError:
            raise UnsupportedContract('Install tactic-stream[postgres] to use PostgreSQL') from None
        return psycopg.connect(dbname=database or resource.get_database(), host=resource.get_host(),
                               port=resource.get_port() or 5432, user=resource.get_user(),
                               password=resource.get_password(), connect_timeout=5, autocommit=autocommit)

    def initialize(self, resource, password_hash, login='admin', maintenance_database='postgres'):
        """Explicit first installation owns a new database, never an existing one."""
        import json
        from importlib.resources import files
        from pyasm.search.storage import Store
        database = resource.get_database()
        with self._connect(resource, maintenance_database, autocommit=True) as maintenance:
            import psycopg
            if maintenance.execute('SELECT 1 FROM pg_database WHERE datname=%s', (database,)).fetchone():
                raise FileExistsError('PostgreSQL database already exists: ' + database)
            maintenance.execute(psycopg.sql.SQL('CREATE DATABASE {}').format(psycopg.sql.Identifier(database)))
            try:
                with self._connect(resource) as db:
                    schema = resource.get_schema() or 'public'
                    if schema != 'public':
                        db.execute(psycopg.sql.SQL('CREATE SCHEMA {}').format(psycopg.sql.Identifier(schema)))
                    db.execute(psycopg.sql.SQL('SET search_path TO {}').format(psycopg.sql.Identifier(schema)))
                    resources = files('tactic_stream') / 'compatibility'
                    # Shipped DDL has whole-line comments, including semicolons.
                    ddl = (resources / 'bootstrap.sql').read_text(encoding='utf-8')
                    ddl = '\n'.join(line for line in ddl.splitlines() if not line.lstrip().startswith('--'))
                    for statement in ddl.split(';'):
                        if statement.strip():
                            db.execute(self._bootstrap_statement(statement))
                    self._insert_registry(db, json.loads((resources / 'bootstrap_registry.json').read_text(encoding='utf-8')))
                    db.execute("INSERT INTO project (code,title) VALUES ('admin','Administration'),('sthpw','System')")
                    db.execute('INSERT INTO login (code,login,password) VALUES (%s,%s,%s)', (login, login, password_hash))
                    db.execute("INSERT INTO login_group (code,login_group) VALUES ('admin','admin')")
                    db.execute('INSERT INTO login_in_group (code,login,login_group) VALUES (%s,%s,%s)',
                               (login + ':admin', login, 'admin'))
                    self._upgrade_schema(db, Store._get_upgrade())
            except Exception:
                # Created exclusively above; no FORCE, no termination of other sessions.
                maintenance.execute(psycopg.sql.SQL('DROP DATABASE {}').format(psycopg.sql.Identifier(database)))
                raise

    def upgrade(self, resource, upgrade=None):
        from pyasm.search.storage import Store
        with self._connect(resource) as db:
            import psycopg
            db.execute(psycopg.sql.SQL('SET search_path TO {}').format(psycopg.sql.Identifier(resource.get_schema() or 'public')))
            return self._upgrade_schema(db, Store._get_upgrade() if upgrade is None else upgrade)

    @staticmethod
    def _insert_registry(db, rows):
        from psycopg.rows import dict_row
        from pyasm.search.storage import identifier
        changed = False
        with db.cursor(row_factory=dict_row) as cursor:
            for row in rows:
                row = {name: value for name, value in row.items() if name != 'id'}
                existing = cursor.execute('SELECT * FROM search_object WHERE search_type=%s', (row['search_type'],)).fetchone()
                if existing:
                    if any(existing[name] != row[name] for name in ('database', 'table_name', 'class_name')):
                        raise ValueError('Conflicting schema registry entry: ' + row['search_type'])
                    continue
                names = ','.join(identifier(name) for name in row)
                cursor.execute('INSERT INTO search_object (%s) VALUES (%s)' % (names, ','.join('%s' for _ in row)), list(row.values()))
                changed = True
        return changed

    def _upgrade_schema(self, db, upgrade):
        changed = False
        for table, statement in upgrade['tables'].items():
            if not db.execute('SELECT 1 FROM information_schema.tables WHERE table_schema=current_schema() AND table_name=%s', (table,)).fetchone():
                db.execute(self._bootstrap_statement(statement))
                changed = True
        for migration in upgrade['columns']:
            if not db.execute('SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() '
                              'AND table_name=%s AND column_name=%s', (migration['table'], migration['column'])).fetchone():
                db.execute(self._bootstrap_statement(migration['sql']))
                if migration.get('after_add_sql'):
                    db.execute(migration['after_add_sql'])
                changed = True
        for migration in upgrade.get('text_columns', []):
            table, column = migration['table'], migration['column']
            row = db.execute('SELECT data_type FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s AND column_name=%s', (table, column)).fetchone()
            if row and row[0] != 'text':
                from pyasm.search.storage import identifier
                db.execute('ALTER TABLE %s ALTER COLUMN %s TYPE text' % (identifier(table), identifier(column)))
                changed = True
        for migration in upgrade.get('nullable', []):
            table, column = migration['table'], migration['column']
            row = db.execute('SELECT is_nullable FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s AND column_name=%s', (table, column)).fetchone()
            if row and row[0] == 'NO':
                from pyasm.search.storage import identifier
                db.execute('ALTER TABLE %s ALTER COLUMN %s DROP NOT NULL' % (identifier(table), identifier(column)))
                changed = True
        for migration in upgrade.get('drop_constraints', []):
            from pyasm.search.storage import identifier
            exists = db.execute('SELECT 1 FROM pg_constraint WHERE conrelid=%s::regclass AND conname=%s',
                                (migration['table'], migration['constraint'])).fetchone()
            if exists:
                db.execute('ALTER TABLE %s DROP CONSTRAINT %s' % (identifier(migration['table']), identifier(migration['constraint'])))
                changed = True
        for index in upgrade['indexes']:
            if not db.execute('SELECT 1 FROM pg_indexes WHERE schemaname=current_schema() AND indexname=%s', (index['name'],)).fetchone():
                db.execute(index['sql'])
                changed = True
        return self._insert_registry(db, upgrade['registry']) or changed

    def get_parameter(self):
        return '%s'

    def get_bound_regex_filter(self, column, regex, op='EQI'):
        if op not in self.REGEX_OPERATORS:
            raise SetupException('Invalid op [%s]. Try EQ, EQI, NEQ, or NEQI' % op)
        return '%s %s %%s' % (column, self.REGEX_OPERATORS[op]), str(regex or '')

    def has_savepoint(self):
        return True

    def set_savepoint(self, name='save_pt'):
        from pyasm.search.storage import identifier
        return 'SAVEPOINT %s' % identifier(name)

    def rollback_savepoint(self, name='save_pt', release=False):
        from pyasm.search.storage import identifier
        return 'ROLLBACK TO SAVEPOINT %s' % identifier(name)

    def release_savepoint(self, name='save_pt'):
        from pyasm.search.storage import identifier
        return 'RELEASE SAVEPOINT %s' % identifier(name)

    def get_timestamp_now(self, offset=None, type=None, op='+'):
        from pyasm.search.sql import Sql
        if not offset:
            return 'now()'
        if op not in ('+', '-'):
            raise ValueError('Invalid interval operator')
        return 'now() %s %s::interval' % (op, Sql.quote('%s %s' % (offset, type or 'day')))

    def get_timestamp_filter(self, value):
        expression = super().get_timestamp_filter(value)
        if expression is not None or not isinstance(value, str):
            return expression
        if re.fullmatch(r"now\(\)(?: [+-] '[+-]?\d+(?:\.\d+)? (?:microsecond|millisecond|second|minute|hour|day|week|month|quarter|year|decade|century|centuries|millennium|millennia)s?'::interval)?", value, re.I):
            return value
        if re.fullmatch(r'CURRENT_TIMESTAMP\([0-6]\)', value, re.I):
            return value
        if value.upper().startswith(('NOW(', 'CURRENT_TIMESTAMP', 'DATETIME(')):
            raise ValueError('Invalid timestamp expression for PostgreSQL')
        return None

    def process_value(self, name, value, column_type='varchar'):
        import re
        if value == 'NULL':
            return {'value': value, 'quoted': False}
        if column_type in ('timestamp', 'datetime', 'datetime2'):
            expression = self.get_timestamp_filter(value)
            if expression is not None:
                return {'value': expression, 'quoted': False}
        if column_type == 'boolean':
            return {'value': value in ('true', 'True', 1, '1', True), 'quoted': False}
        if column_type in ('json', 'jsonb') and isinstance(value, str) and value in (
                self.get_json_counter_update(name, 'invalid_logins'),
                self.get_json_counter_update(name, 'invalid_logins', True)):
            return {'value': value, 'quoted': False}
        if column_type in ('json', 'jsonb') and isinstance(value, str):
            try:
                json.loads(value)
            except (ValueError, TypeError):
                return {'value': json.dumps(value), 'quoted': True}
        if column_type in ('decimal', 'numeric'):
            if isinstance(value, str) and value.startswith("Decimal('") and value.endswith("')"):
                value = value[9:-2]
            number = Decimal(str(value))
            return {'value': number, 'quoted': not number.is_finite()}

    def get_create_sequence(self, name):
        from pyasm.search.storage import identifier
        return 'CREATE SEQUENCE %s START WITH 1 INCREMENT BY 1 NO MAXVALUE CACHE 1' % identifier(name)

    def get_nextval(self, sequence):
        from pyasm.search.sql import Sql
        from pyasm.search.storage import identifier
        return 'nextval(%s)' % Sql.quote(identifier(sequence))

    def get_currval(self, sequence):
        from pyasm.search.sql import Sql
        from pyasm.search.storage import identifier
        return 'currval(%s)' % Sql.quote(identifier(sequence))

    def get_nextval_select(self, sequence, db_resource=None):
        from pyasm.search.storage import identifier
        from pyasm.search.sql import Sql
        schema = db_resource.get_schema() if db_resource else None
        name = (identifier(schema) + '.' if schema and schema != 'public' else '') + identifier(sequence)
        return 'select nextval(%s)' % Sql.quote(name)

    def get_currval_select(self, sequence, db_resource=None):
        return self.get_nextval_select(sequence, db_resource).replace('nextval(', 'currval(', 1)

    def get_setval_select(self, sequence, num):
        from pyasm.search.sql import Sql
        from pyasm.search.storage import identifier
        return 'select setval(%s, %d)' % (Sql.quote(identifier(sequence)), int(num))

    def get_reset_table_sequence_statement(self, table, database=None):
        from pyasm.search.sql import DbContainer
        from pyasm.search.storage import identifier
        sql = DbContainer.get(database)
        next_id = sql.get_int('SELECT COALESCE(MAX(id), 0) + 1 FROM %s' % identifier(table))
        return 'ALTER SEQUENCE %s RESTART WITH %d' % (identifier(self.get_sequence_name(table)), next_id)

    def get_regex_filter(self, column, regex, op='EQI'):
        from pyasm.search.sql import Sql
        from pyasm.search.storage import identifier
        operators = self.REGEX_OPERATORS
        if op not in operators:
            raise SetupException('Invalid op [%s]. Try EQ, EQI, NEQ, or NEQI' % op)
        parts = column.replace('->>', '->').split('->', 1)
        name = identifier(parts[0])
        if len(parts) == 2:
            name += '->>' + Sql.quote(parts[1])
        return '%s %s %s' % (name, operators[op], Sql.quote(regex))

    def get_json_counter_update(self, column, key, reset=False):
        from pyasm.search.sql import Sql
        from pyasm.search.storage import identifier
        if not isinstance(key, str):
            raise ValueError('A JSON key must be a string')
        name, path = identifier(column), Sql.quote(key)
        count = '0' if reset else 'COALESCE((%s->>%s)::bigint, 0) + 1' % (name, path)
        return "jsonb_set(COALESCE(%s, '{}'::jsonb), ARRAY[%s]::text[], to_jsonb((%s)::bigint))" % (name, path, count)

    @classmethod
    def get_column_info(cls, db_resource, table, use_cache=True):
        from pyasm.search.sql import DbContainer, DbResource, Sql
        sql = db_resource if isinstance(db_resource, Sql) else None
        resource = sql.get_db_resource() if sql else db_resource
        if not DbResource.is_instance(resource):
            resource = DbResource.get_default(resource)
        cache = Container.get('DatabaseImpl:column_info')
        if cache is None:
            cache = {}
            Container.put('DatabaseImpl:column_info', cache)
        key = (resource._get_connection_key(), table)
        if use_cache and key in cache:
            return cache[key]
        sql = sql or DbContainer.get(resource)
        schema = resource.get_schema() or 'public'
        query = ('SELECT column_name, data_type, is_nullable, character_maximum_length '
                 'FROM information_schema.columns WHERE table_name = %s AND table_schema = %s '
                 'ORDER BY ordinal_position') % (Sql.quote(table), Sql.quote(schema))
        result = {}
        for name, data_type, nullable, size in sql.do_query(query):
            if data_type == 'character varying':
                data_type = 'varchar'
            elif data_type in ('integer', 'smallint'):
                data_type = 'integer'
            elif data_type == 'jsonb':
                data_type = 'json'
            elif data_type.startswith('timestamp'):
                data_type = 'timestamp'
            elif data_type.startswith('time '):
                data_type = 'time'
            result[name] = {'data_type': data_type, 'nullable': nullable == 'YES', 'size': size}
        # Refresh must also replace stale request metadata after a schema change.
        cache[key] = result
        return result

    def get_column_types(self, database, table, use_cache=True):
        return {name: info['data_type'] for name, info in self.get_column_info(database, table, use_cache).items()}

    def get_table_info(self, db_resource):
        from pyasm.search.sql import DbContainer, Sql
        sql = db_resource if isinstance(db_resource, Sql) else DbContainer.get(db_resource)
        resource = sql.get_db_resource()
        cache = Container.get('DatabaseImpl:table_info')
        if cache is None:
            cache = {}
            Container.put('DatabaseImpl:table_info', cache)
        key = resource._get_connection_key()
        if key not in cache:
            schema = Sql.quote(resource.get_schema() or 'public')
            # Original table lookup leaked other schemas; views always used public.
            query = ('SELECT tablename FROM pg_tables WHERE schemaname = %s '
                     'UNION SELECT viewname FROM pg_views WHERE schemaname = %s') % (schema, schema)
            cache[key] = {name: name for name, in sql.do_query(query)}
        return cache[key]

    def get_database_type(self):
        return "PostgreSQL"

    def get_page(self, limit=None, offset=0, table_input=0, already_in_where_clause=0):
        '''get the pagination sql based on limit and offset'''
        if limit == None:
            return None

        parts = []
        parts.append("LIMIT %s" % limit)
        if offset:
            parts.append("OFFSET %s" % offset)
        return " ".join(parts)

    def get_boolean(self, not_null=False):
        parts = []
        parts.append("boolean")
        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_serial(self, length=4, not_null=False):
        # Original silently used int4 even when callers requested int8.
        if length not in (2, 4, 8):
            raise ValueError('Serial length must be 2, 4 or 8')
        return {2: 'smallserial', 4: 'serial', 8: 'bigserial'}[length]

    def get_int(self, length=4, not_null=False):
        parts = []
        parts.append("int%s" % length)
        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_float(self, not_null=False):
        parts = []
        parts.append("float")
        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_text(self, not_null=False):
        parts = []
        parts.append("text")
        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_char(self, length=256, not_null=False):
        assert length
        parts = []
        parts.append("char(%s)" % length)
        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_varchar(self, length=256, not_null=False):
        if not length:
            length = 256

        if length in [-1, 'max']:
            return self.get_text(not_null=not_null)
        parts = []
        parts.append("varchar(%s)" % length)
        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_nvarchar(self, length=256, not_null=False):
        return self.get_varchar(length=length, not_null=not_null)

    def get_timestamp(self, default=None, not_null=False, timezone=False):
        parts = []
        if timezone:
            parts.append("timestamp with time zone")
        else:
            parts.append("timestamp")
        if default:
            if default == "now":
                parts.append("DEFAULT %s" % self.get_timestamp_now())
            else:
                parts.append("DEFAULT %s" % default)

        if not_null:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_json(self, not_null=False):
       parts = []
       parts.append("jsonb")
       if not_null:
           parts.append("NOT NULL")
       return " ".join(parts)

    def has_sequences(self):
        return True

    def get_sequence_name(self, table, database=None):
        from pyasm.search import SearchType
        if isinstance(table, SearchType):
            search_type = table
            table = search_type.get_table()
            id_col = search_type.get_search_type_id_col()
            if id_col:
                return "%s_%s_seq" % (table, id_col)

        return "%s_id_seq" % table
