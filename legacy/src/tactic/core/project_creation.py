"""Native project creation keeps CreateProjectCmd's lifecycle.

Only a freshly created SQLite project's bootstrap is adapted. Existing projects
are never upgraded here. DDL/files and the original mid-command commits are NOT
represented as an atomic, safely retryable operation.
"""
from pathlib import Path
from tactic.command.create_project_cmd import CreateProjectCmd


class NativeCreateProjectCmd(CreateProjectCmd):
    def upgrade(self):
        from pyasm.biz import Project
        from pyasm.common import Environment
        from pyasm.search import DbContainer, Search
        from pyasm.search.upgrade.upgrade_db import Upgrade
        code = self.kwargs['project_code']
        obj = Project.get_by_code(code)
        db = DbContainer.get(obj.get_project_db_resource())
        state = None
        if db.get_database_type() == 'Sqlite':
            from tactic.core.sqlite_upgrade import prepare_config_schema, repair_identity_columns, SQLiteUpgrade, split_sql, strip_comments, create_parts, PAIR_TABLES, quote
            if db.get_connection() is None:
                db.connect()
            connection = db.get_connection()
            registry = {s.get_value('search_type'): s.get_value('table_name')
                        for s in Search('sthpw/search_object').get_sobjects()}
            root = Path(Environment.get_install_dir()) / 'src/pyasm/search/upgrade/sqlite'
            journal = []
            # These tables were just imported into a NEW empty project. Rename
            # stock-prefixed tables to the actual registry names before upgrade;
            # do not leave a parallel empty configuration store.
            probe=SQLiteUpgrade(connection)
            for name in PAIR_TABLES:
                canonical=registry.get('config/'+name,name).replace('{public}.','').replace('public.','')
                if canonical not in (name,'spt_'+name):
                    raise RuntimeError('Custom configuration table mapping needs a project adapter')
                alternate='spt_'+name if canonical==name else name
                if probe.exists(alternate) and not probe.exists(canonical):
                    connection.execute('ALTER TABLE '+quote(alternate)+' RENAME TO '+quote(canonical))
            aliases = prepare_config_schema(connection, (root/'config_schema.sql').read_text(encoding='utf-8'), registry, journal)
            # Original config/custom_property registration points to this stock
            # definition, which is absent from some project schema distributions.
            for raw in split_sql((root/'sthpw_schema.sql').read_text(encoding='utf-8')):
                sql = strip_comments(raw).strip()
                if sql.startswith('CREATE TABLE') and create_parts(sql)[0] == 'custom_property':
                    SQLiteUpgrade(connection, journal=journal, method=code+'/stock-custom-property').execute(sql)
            repair_identity_columns(connection, journal)
            db.commit()
            db.clear_table_cache()
            state = {'aliases': {code: aliases}, 'statements': journal, 'completed': [], 'repair_from': None}
        upgrade = Upgrade(Environment.get_release_version(), is_forced=True,
                          project_code=code, quiet=True, is_confirmed=True, sqlite_managed=state)
        upgrade.execute()
        if upgrade.errors:
            raise RuntimeError('Original project upgrade reported errors; project needs inspection before retry')
        if state is not None:
            from tactic.core.sqlite_upgrade import repair_identity_columns, identity_issues
            from tactic.core.schema_health import inspect_schema
            # Upgrade may rotate the thread's database handles.
            db = DbContainer.get(obj.get_project_db_resource())
            if db.get_connection() is None:
                db.connect()
            connection = db.get_connection()
            repair_identity_columns(connection, state['statements'])
            health = inspect_schema(lambda table: [r[1] for r in connection.execute(
                'PRAGMA table_info("'+table.replace('"','""')+'")')], registry, include_core=False)
            if not health['ready'] or identity_issues(connection):
                raise RuntimeError('New project schema failed readiness verification')
            if [r[0] for r in connection.execute('PRAGMA integrity_check')] != ['ok']:
                raise RuntimeError('New project database failed integrity check')
            db.commit()
            db.clear_table_cache()
            self.info['native_schema_checked'] = True

    def import_default_side_bar(self):
        from pyasm.biz import Project
        # Original lookup runs before set_project. Bind before BOTH lookup/create.
        Project.set_project(self.kwargs['project_code'])
        return super().import_default_side_bar()
