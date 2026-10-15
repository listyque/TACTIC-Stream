"""Unchanged journal-writing server script executed by both TACTIC kernels."""
from pyasm.command import Command
from pyasm.common import Common, Environment
from pyasm.search import DbContainer, Search, SearchType, Transaction, TransactionLog
from pyasm.security import Security


def normalized(value, name=''):
    if name == 'timestamp' and value:
        # Real insert timestamps differ between subprocesses; their validity
        # and generated SQL are checked separately on the owned runtime.
        return '<timestamp>'
    if isinstance(value, dict):
        return {key: normalized(item, key) for key, item in value.items()}
    if isinstance(value, list):
        return [normalized(item) for item in value]
    if isinstance(value, str) and value.startswith('zlib:'):
        return {'compressed_xml': Common.decompress_transaction(value)}
    return value


class JournalWriteCommand(Command):
    def __init__(self, case):
        super().__init__()
        self.case = case

    def execute(self):
        transaction = self.get_transaction()
        # Explicit supported low-level branch; default automatic recording and
        # remote queues are tested as guarded, rather than silently disabled.
        transaction.set_record(False)
        transaction.set_sync(False)
        case = self.case
        sql = DbContainer.get('sthpw')
        if case.get('redo'):
            sql.do_update("INSERT INTO transaction_log (id,code,login,type,namespace) VALUES (10,'REDO','admin','redo','one')")
            sql.do_update("INSERT INTO transaction_log (id,code,login,type,namespace) VALUES (11,'OTHER','other','redo','one')")
            sql.do_update("INSERT INTO transaction_log (id,code,login,type,namespace) VALUES (12,'UNDO','admin','undo','one')")
            sql.do_update("INSERT INTO sobject_list (code,search_type,search_code) VALUES ('INDEX','sthpw/transaction_log','REDO')")
        if case.get('cached_redo'):
            Search.get_by_code('sthpw/transaction_log', 'REDO')
        if case.get('operation') == 'delete_redo':
            TransactionLog.delete_all_redo()
            log = None
        else:
            log = TransactionLog.create('TestCommand', case['xml'], 'Описание', title='Title',
                                        state=case.get('state'), keywords=case.get('keywords'))
        if case.get('index_again'):
            TransactionLog.create_sobject_log(log)
        if case.get('update_log'):
            log.set_value('description', 'Updated')
            log.commit(triggers=False)
        if case.get('id_override'):
            log.set_id(99)
            log.commit(triggers='none')
        if case.get('change_code'):
            log.set_value('code', 'CHANGED')
            log.commit(triggers='none')
        if case.get('force_insert'):
            log.set_force_insert()
            log.set_update_data({'login': 'admin', 'description': 'Copy', 'type': 'undo',
                                 'namespace': 'one', 'command': 'TestCommand'})
            log.commit(triggers=False)
        if case.get('fail'):
            raise ValueError('rollback after journal write')
        return {'log': normalized(log.get_data()) if log else None,
                'has_updates': log.has_updates if log else None,
                'pending': log.update_data.copy() if log else None,
                'cached_redo': bool(Search.get_by_code('sthpw/transaction_log', 'REDO')) if case.get('cached_redo') else None}


def run(case):
    previous = Environment.get_security()
    security = Security()
    Environment.set_security(security)
    try:
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
        sql = DbContainer.get('sthpw')
        for table in ['sobject_log', 'transaction_log', 'sobject_list', 'change_timestamp']:
            sql.do_update('DELETE FROM "' + table + '"')
        sql.do_update("DELETE FROM sqlite_sequence WHERE name IN ('transaction_log','sobject_log','sobject_list','change_timestamp')")
        try:
            result = {'result': Command.execute_cmd(JournalWriteCommand(case))}
        except Exception as error:
            result = {'error': type(error).__name__, 'message': str(error)}
        if case.get('fail'):
            result['rolled_back_cached_log'] = bool(Search.get_by_code('sthpw/transaction_log', 'TRANSACTION00000001'))
        for table in ['transaction_log', 'sobject_log', 'sobject_list', 'change_timestamp']:
            result[table] = normalized([obj.get_data() for obj in Search('sthpw/' + table).get_sobjects()])
        result['admin'] = security.is_admin()
        result['counter'] = Transaction.get().counter
        return result
    finally:
        Environment.set_security(previous)
