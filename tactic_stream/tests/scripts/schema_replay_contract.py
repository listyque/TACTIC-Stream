"""Unchanged column replay script; original loses values on Redo."""
from pyasm.biz import Project
from pyasm.command import Command, UndoCmd, RedoCmd
from pyasm.common import Environment
from pyasm.search import Search, AlterTableUndo, DbContainer, TransactionLog
from pyasm.security import Security
from pyasm.web.api_xmlrpc import ApiXMLRPC


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        sql = DbContainer.get(Project.get().get_project_db_resource())
        column = 'api_value' if case.get('api') else 'undo_value'
        def logs():
            search = Search(TransactionLog.SEARCH_TYPE)
            search.add_order_by('id desc')
            return search.get_sobjects()
        before = len(logs())
        def add():
            if case.get('api'):
                api = ApiXMLRPC()
                api.set_protocol('local')
                api.add_column_to_search_type(dict(project='one'), 'contract/entity', column, 'integer')
            else:
                sql.do_update('ALTER TABLE entity ADD COLUMN "%s" integer' % column)
                sql.clear_table_cache()
                AlterTableUndo.log_add(sql.get_db_resource(), 'entity', column, 'integer')
                sql.do_update("UPDATE entity SET undo_value=51 WHERE code='A'")
        cmd = Command()
        cmd.get_transaction().set_sync(False)
        cmd.execute = add
        Command.execute_cmd(cmd)
        if case.get('api'):
            return len(logs()) - before
        log = logs()[0]
        def apply(cmd):
            cmd.get_transaction().set_sync(False)
            cmd.get_transaction().set_record(False)
            Command.execute_cmd(cmd)
            sql.clear_table_cache()
        apply(UndoCmd(transaction_log=log))
        absent = column not in sql.get_column_info('entity', use_cache=False)
        apply(RedoCmd(transaction_log=log))
        return [absent, sql.do_query("SELECT undo_value FROM entity WHERE code='A'")[0][0]]
    finally:
        Environment.set_security(previous)
