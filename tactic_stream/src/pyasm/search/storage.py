"""Owned SQLite/PostgreSQL system storage and native project database resources.

Store mutations are limited to explicit bootstrap/upgrades and authentication.
Reads borrow active Sql connections. SObject persistence awaits journal/triggers.
"""
from contextlib import contextmanager, nullcontext
from importlib.resources import files
import json
from pathlib import Path
import re
import sqlite3

from pyasm.common.errors import UnsupportedContract
from pyasm.search.keys import breakup_search_type


def identifier(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("Invalid SQL identifier")
    return '"' + value.replace('"', '""') + '"'


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir).resolve()

    def database_path(self, database: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", database):
            raise UnsupportedContract("Unsupported database name")
        from pyasm.search.search import _context
        context = _context.get(None)
        paths = context.container.info.setdefault('Store:database_paths', {}) if context else {}
        key = (self.data_dir, database)
        if key in paths:
            return paths[key]
        path = (self.data_dir / "db" / (database + ".db")).resolve()
        if not path.is_relative_to(self.data_dir):
            raise ValueError("Database must remain inside its data directory")
        paths[key] = path
        return path

    def get_db_resource(self, database='sthpw'):
        from pyasm.search.search import RequestContext, request_context, _context
        from pyasm.search.sql import DbResource
        context = _context.get(None)
        if context and context.store.data_dir == self.data_dir:
            return DbResource.get_default(database)
        with request_context(RequestContext(self, 'admin')):
            return DbResource.get_default(database)

    def is_initialized(self):
        resource = self.get_db_resource()
        if resource.get_vendor() == 'Sqlite':
            return self.database_path('sthpw').is_file()
        import psycopg
        try:
            with resource.get_database_impl()._connect(resource) as db:
                db.execute('SET TRANSACTION READ ONLY')
                return all(db.execute('SELECT to_regclass(%s)', (table,)).fetchone()[0]
                           for table in ('search_object', 'login', 'project', 'ticket'))
        except psycopg.OperationalError:
            return False

    @contextmanager
    def connection(self, database="sthpw", *, write=False):
        from pyasm.search.sql import DbContainer, DbResource
        from pyasm.search.search import RequestContext, request_context, _context
        if not DbResource.is_instance(database):
            database = self.get_db_resource(database)
        if DbResource.is_instance(database):
            if database.get_vendor() == 'PostgreSQL':
                if write:
                    raise UnsupportedContract('Use Sql for PostgreSQL writes; Store only borrows reads')
                if _context.get(None) is None:
                    with request_context(RequestContext(self, 'admin')):
                        with self.connection(database) as db:
                            yield db
                    return
                with DbContainer.get(database).read_connection() as db:
                    yield db
                return
            database = database.get_database()
        context = _context.get(None)
        state = context.container.get_data() if context else {}
        transactions = state.get("Transaction:transaction") or []
        if write:
            if state.get("Command:executing") or any(tx.is_in_transaction() for tx in transactions):
                raise UnsupportedContract("Use Sql inside Command/Transaction; direct Store writes cannot participate in rollback")
        elif context and context.store.data_dir == self.data_dir and (
                any(tx.is_in_transaction() for tx in transactions) or state.get("DbContainer::thread_pool")):
            sql = DbContainer.get(DbResource.get_default(database))
            # Borrow the transaction's connection without committing or closing it.
            with sql.read_connection() as db:
                yield db
            return
        # Read-only connections belong to this request, never to a user/session cache.
        # An active Sql/Transaction above still supplies its own connection.
        readers = context.read_connections if context and context.store.data_dir == self.data_dir else None
        if not write and readers is not None and database in readers:
            with readers[database] as db:
                yield db
            return
        path = self.database_path(database)
        mode = "rw" if write else "ro"
        db = sqlite3.connect(path.as_uri() + "?mode=" + mode, uri=True, timeout=5)
        from pyasm.search.database_impl import SqliteImpl
        SqliteImpl.configure_connection(db)
        db.row_factory = sqlite3.Row
        try:
            if not write:
                db.execute("PRAGMA query_only=ON")
                if readers is not None:
                    readers[database] = db
            with db:
                yield db
        finally:
            if write or readers is None or readers.get(database) is not db:
                db.close()
            if write and context and context.store.data_dir == self.data_dir:
                from pyasm.search.sql import Sql
                Sql.clear_table_cache()

    def initialize(self, password_hash: str, login: str = "admin"):
        """Create a new owned database, refusing every existing file."""
        if not login or len(login) > 100:
            raise ValueError("A login of 1..100 characters is required")
        resource = self._configured_resource()
        if resource.get_vendor() == 'PostgreSQL':
            return resource.get_database_impl().initialize(resource, password_hash, login)
        path = self.database_path("sthpw")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=False)
        try:
            resources = files("tactic_stream") / "compatibility"
            with self.connection(write=True) as db:
                db.executescript((resources / "bootstrap.sql").read_text(encoding="utf-8"))
                for row in json.loads((resources / "bootstrap_registry.json").read_text(encoding="utf-8")):
                    row.pop("id", None)
                    names = ",".join(identifier(name) for name in row)
                    db.execute(f"INSERT INTO search_object ({names}) VALUES ({','.join('?' for _ in row)})",
                               list(row.values()))
                # Only bootstrap metadata is seeded; no demo assets/tasks or old users.
                db.executemany("INSERT INTO project (code,title) VALUES (?,?)",
                               [("admin", "Administration"), ("sthpw", "System")])
                db.execute('INSERT INTO login (code,login,password) VALUES (?,?,?)',
                           (login, login, password_hash))
                db.execute("INSERT INTO login_group (code,login_group) VALUES ('admin','admin')")
                db.execute("INSERT INTO login_in_group (code,login,login_group) VALUES (?,?,?)",
                           (login + ":admin", login, "admin"))
                self._upgrade_schema(db)
        except Exception:
            # This file was exclusively created above, never an existing database.
            path.unlink()
            raise

    def upgrade(self):
        """Upgrade owned system and registered project schemas, one database at a time."""
        resource = self._configured_resource()
        if resource.get_vendor() == 'PostgreSQL':
            changed = resource.get_database_impl().upgrade(resource)
        else:
            with self.connection(write=True) as db:
                db.execute("BEGIN")
                changed = self._upgrade_schema(db)
        from pyasm.search.search import RequestContext, Search, request_context
        from pyasm.search.sql import DbResource
        upgrade = json.loads((files('tactic_stream') / 'compatibility/config_upgrade.json').read_text(encoding='utf-8'))
        upgrade.update(registry=[], indexes=[])
        with request_context(RequestContext(self, 'admin')):
            visited = {resource._get_connection_key()}
            for project in Search('sthpw/project').get_sobjects():
                project_resource = project.get_project_db_resource()
                key = project_resource._get_connection_key()
                if key in visited:
                    continue
                if key != DbResource.get_default(project_resource.get_database())._get_connection_key():
                    raise UnsupportedContract('Automatic upgrade of external project resources is not migrated')
                if project_resource.get_vendor() == 'PostgreSQL':
                    changed = project_resource.get_database_impl().upgrade(project_resource, upgrade) or changed
                else:
                    with self.connection(project_resource, write=True) as db:
                        db.execute('BEGIN')
                        changed = self._upgrade_schema(db, upgrade) or changed
                visited.add(key)
        return changed

    def _configured_resource(self):
        from pyasm.common.common import Container
        from pyasm.common.config import Config
        from pyasm.search.search import RequestContext, request_context, _context
        from pyasm.search.sql import DbResource
        if _context.get(None) and (Container.get('Command:executing') or any(tx.is_in_transaction() for tx in Container.get_seq('Transaction:transaction'))):
            raise UnsupportedContract('Bootstrap/upgrade cannot run inside Command/Transaction')
        with request_context(RequestContext(self, 'admin')):
            database = Config.get_value('database', 'sobject_database', default='sthpw')
            return DbResource.get_default(database, use_cache=False, use_config=True)

    @staticmethod
    def _get_upgrade():
        upgrade = json.loads((files("tactic_stream") / "compatibility/schema_upgrade.json").read_text(encoding="utf-8"))
        journal = json.loads((files('tactic_stream') / 'compatibility/journal_upgrade.json').read_text(encoding='utf-8'))
        pipeline = json.loads((files('tactic_stream') / 'compatibility/pipeline_upgrade.json').read_text(encoding='utf-8'))
        triggers = json.loads((files('tactic_stream') / 'compatibility/trigger_upgrade.json').read_text(encoding='utf-8'))
        security = json.loads((files('tactic_stream') / 'compatibility/security_upgrade.json').read_text(encoding='utf-8'))
        persistence = json.loads((files('tactic_stream') / 'compatibility/persistence_upgrade.json').read_text(encoding='utf-8'))
        preferences = json.loads((files('tactic_stream') / 'compatibility/preference_upgrade.json').read_text(encoding='utf-8'))
        business = json.loads((files('tactic_stream') / 'compatibility/business_upgrade.json').read_text(encoding='utf-8'))
        workflow = json.loads((files('tactic_stream') / 'compatibility/workflow_upgrade.json').read_text(encoding='utf-8'))
        scripts = json.loads((files('tactic_stream') / 'compatibility/script_upgrade.json').read_text(encoding='utf-8'))
        snapshots = json.loads((files('tactic_stream') / 'compatibility/snapshot_upgrade.json').read_text(encoding='utf-8'))
        connections = json.loads((files('tactic_stream') / 'compatibility/connection_upgrade.json').read_text(encoding='utf-8'))
        plugins = json.loads((files('tactic_stream') / 'compatibility/plugin_upgrade.json').read_text(encoding='utf-8'))
        config = json.loads((files('tactic_stream') / 'compatibility/config_upgrade.json').read_text(encoding='utf-8'))
        upgrade['naming_revision'] = config.get('naming_revision', False)
        upgrade['tables'].update(config['tables'])
        upgrade['registry'].extend(config['registry'])
        upgrade['tables'].update(plugins['tables'])
        upgrade['registry'].extend(plugins['registry'])
        upgrade['tables'].update(connections['tables'])
        upgrade['registry'].extend(connections['registry'])
        upgrade['tables'].update(snapshots['tables'])
        upgrade['registry'].extend(snapshots['registry'])
        upgrade['tables'].update(scripts['tables'])
        upgrade['registry'].extend(scripts['registry'])
        upgrade['tables'].update(workflow['tables'])
        upgrade['registry'].extend(workflow['registry'])
        upgrade['tables'].update(business['tables'])
        upgrade['registry'].extend(business['registry'])
        upgrade['tables'].update(preferences['tables'])
        upgrade['registry'].extend(preferences['registry'])
        upgrade['tables'].update(persistence['tables'])
        upgrade['registry'].extend(persistence['registry'])
        upgrade['tables'].update(journal['tables'])
        upgrade['registry'].extend(journal['registry'])
        upgrade['tables'].update(pipeline['tables'])
        upgrade['registry'].extend(pipeline['registry'])
        upgrade['tables'].update(triggers['tables'])
        upgrade['registry'].extend(triggers['registry'])
        upgrade['columns'] = [
            {'table': 'schema', 'column': 'project_code', 'sql': upgrade['project_code_sql']},
            {'table': 'project', 'column': 'database', 'sql': upgrade['project_database_sql']},
        ] + journal['columns'] + pipeline['columns'] + security['columns'] + persistence['columns'] + business['columns'] + workflow['columns'] + snapshots['columns'] + connections['columns'] + config['columns']
        upgrade['nullable'] = snapshots.get('nullable', [])
        # Handler's profile editor includes address; the old login schema did not.
        upgrade['columns'].append({'table':'login', 'column':'address', 'sql':'ALTER TABLE "login" ADD "address" text;'})
        upgrade['text_columns'] = config['text_columns']
        upgrade['drop_constraints'] = config['drop_constraints']
        upgrade['indexes'] = [index for part in (journal, workflow, preferences, persistence, snapshots, connections, security)
                              for index in part.get('indexes', [])]
        return upgrade

    @classmethod
    def _upgrade_schema(cls, db, upgrade=None):
        upgrade = cls._get_upgrade() if upgrade is None else upgrade
        changed = False
        for table, sql in upgrade["tables"].items():
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                db.execute(sql)
                changed = True
        for migration in upgrade['columns']:
            if migration['column'] not in {row['name'] for row in db.execute('PRAGMA table_info(%s)' % identifier(migration['table']))}:
                db.execute(migration['sql'])
                if migration.get('after_add_sql'):
                    db.execute(migration['after_add_sql'])
                changed = True
        for migration in upgrade.get('nullable', []):
            changed = cls._drop_not_null(db, migration['table'], migration['column']) or changed
        for migration in upgrade.get('drop_constraints', []):
            changed = cls._drop_constraint(db, migration['table'], migration['constraint']) or changed
        for index in upgrade['indexes']:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (index['name'],)).fetchone():
                db.execute(index['sql'])
                changed = True
        if upgrade.get('naming_revision'):
            from pyasm.search.database_impl import configuration_revision_statements
            for statement in configuration_revision_statements('Sqlite'):
                db.execute(statement)
        for row in upgrade["registry"]:
            row.pop("id", None)
            existing = db.execute("SELECT * FROM search_object WHERE search_type=?", (row["search_type"],)).fetchone()
            if existing:
                if any(existing[name] != row[name] for name in ("database", "table_name", "class_name")):
                    raise ValueError("Conflicting schema registry entry: " + row["search_type"])
                continue
            names = ",".join(identifier(name) for name in row)
            db.execute(f"INSERT INTO search_object ({names}) VALUES ({','.join('?' for _ in row)})", list(row.values()))
            changed = True
        return changed

    @staticmethod
    def _drop_not_null(db, table, column):
        columns = list(db.execute('PRAGMA table_info(%s)' % identifier(table)))
        if not any(row['name'] == column and row['notnull'] for row in columns):
            return False
        statement = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
        pattern = r'([,(]\s*"?' + re.escape(column) + r'"?\s+[^,]*?)\s+NOT NULL\b'
        statement, count = re.subn(pattern, r'\1', statement, count=1, flags=re.I)
        if count != 1:
            raise UnsupportedContract('Cannot migrate SQLite column constraint: ' + table + '.' + column)
        Store._rebuild_table(db, table, statement)
        return True

    @staticmethod
    def _drop_constraint(db, table, constraint, execute=None):
        statement = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
        pattern = r',\s*CONSTRAINT\s+"?' + re.escape(constraint) + r'"?\s+UNIQUE\s*\([^)]*\)'
        statement, count = re.subn(pattern, '', statement, count=1, flags=re.I)
        if not count:
            return False
        Store._rebuild_table(db, table, statement, execute)
        return True

    @staticmethod
    def _rebuild_table(db, table, statement, execute=None):
        execute = execute or db.execute
        columns = list(db.execute('PRAGMA table_info(%s)' % identifier(table)))
        temporary = table + '_stream_upgrade'
        if db.execute('SELECT 1 FROM sqlite_master WHERE name=?', (temporary,)).fetchone():
            raise ValueError('Upgrade table already exists: ' + temporary)
        statement = re.sub(r'^CREATE TABLE (?:"[^"]+"|\w+)', 'CREATE TABLE ' + identifier(temporary), statement, count=1, flags=re.I)
        definitions = [row[0] for row in db.execute("SELECT sql FROM sqlite_master WHERE tbl_name=? AND type IN ('index','trigger') AND sql IS NOT NULL", (table,))]
        sequence = None
        if 'AUTOINCREMENT' in statement.upper():
            row = db.execute('SELECT seq FROM sqlite_sequence WHERE name=?', (table,)).fetchone()
            sequence = row[0] if row else None
        names = ','.join(identifier(row[1]) for row in columns)
        execute(statement)
        execute('INSERT INTO %s (%s) SELECT %s FROM %s' % (identifier(temporary), names, names, identifier(table)))
        execute('DROP TABLE ' + identifier(table))
        execute('ALTER TABLE %s RENAME TO %s' % (identifier(temporary), identifier(table)))
        for definition in definitions:
            execute(definition)
        if sequence is not None:
            execute("UPDATE sqlite_sequence SET seq=MAX(seq,%d) WHERE name='%s'" % (int(sequence), table.replace("'", "''")))

    def resolve(self, search_type: str, project: str):
        from pyasm.common import Container
        from pyasm.search.search import _context
        context = _context.get(None)
        cache = Container.get_full_dict('Store:resolve') if context and context.store.data_dir == self.data_dir else {}
        key = (self.data_dir, search_type, project)
        if key in cache:
            definition, database, table = cache[key]
            return definition.copy(), database, table
        parts = breakup_search_type(search_type)
        if not parts.get("namespace") or not parts.get("table") or set(parts) - {
                "search_type", "namespace", "table", "project", "code"}:
            raise UnsupportedContract("Unsupported search type parameters")
        if parts.get("code"):
            raise UnsupportedContract("Object identity belongs in a search key")
        base = parts["search_type"]
        parameter = self.get_db_resource().get_database_impl().get_parameter()
        definition_key = ('definition', self.data_dir, base)
        definition = cache.get(definition_key)
        project_key = ('project', self.data_dir, parts.get('project') or project)
        needs_read = definition is None or (definition['database'] == '{project}' and project_key not in cache)
        with self.connection() if needs_read else nullcontext() as db:
            if definition is None:
                row = db.execute('SELECT * FROM search_object WHERE search_type=' + parameter, (base,)).fetchone()
                if not row:
                    raise LookupError("Unregistered SearchType: " + base)
                definition = dict(row)
                cache[definition_key] = definition
            definition = definition.copy()
            database = definition["database"]
            external = False
            if database == "{project}":
                project_code = parts.get("project") or project
                owner = cache.get(project_key)
                if owner is None:
                    row = db.execute('SELECT * FROM project WHERE code=' + parameter, (project_code,)).fetchone()
                    owner = dict(row) if row else None
                    if owner is not None:
                        cache[project_key] = owner
                if not owner or owner["s_status"] == "retired":
                    raise LookupError("Unknown or retired project")
                database = owner['database'] or project_code
                database = 'sthpw' if database == 'admin' else database
                external = bool(owner['db_resource']) and database != 'sthpw'
        if not external:
            # DbResource already validates the SQLite path on construction.
            self.get_db_resource(database)
        table = definition["table_name"].replace("{public}.", "").replace("public.", "")
        cache[key] = definition.copy(), database, table
        return definition, database, table

    def tables(self, database: str) -> dict:
        from pyasm.search.sql import DbResource
        if not DbResource.is_instance(database):
            database = self.get_db_resource(database)
        if DbResource.is_instance(database):
            if database.get_vendor() == 'PostgreSQL':
                return database.get_database_impl().get_table_info(database)
            database = database.get_database()
        with self.connection(database) as db:
            rows = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return {row["name"]: row["name"] for row in rows}

    def columns(self, database: str, table: str) -> dict:
        from pyasm.search.sql import DbResource
        if not DbResource.is_instance(database):
            database = self.get_db_resource(database)
        if DbResource.is_instance(database):
            if database.get_vendor() == 'PostgreSQL':
                columns = database.get_database_impl().get_column_info(database, table)
                if not columns:
                    raise LookupError('Registered table does not exist')
                return columns
            database = database.get_database()
        with self.connection(database) as db:
            rows = db.execute(f"PRAGMA table_info({identifier(table)})").fetchall()
        if not rows:
            raise LookupError("Registered table does not exist")
        result = {}
        for row in rows:
            data_type, size = row["type"], 0
            match = re.fullmatch(r"(?:character varying|varchar)\((\d+)\)", data_type)
            if match:
                data_type, size = "varchar", int(match[1])
            elif data_type == "varchar":
                size = 256
            elif data_type.startswith("timestamp"):
                data_type = "timestamp"
            result[row["name"]] = {"data_type": data_type,
                                   "size": size, "nullable": row["notnull"] not in (1, 99)}
        return result
