"""Unchanged SObject journal lifecycle in the original and migrated kernels."""
from pyasm.command import Command, UndoCmd, RedoCmd
from pyasm.common import Environment
from pyasm.search import Search, SearchType, TransactionLog
from pyasm.security import Security
from pyasm.biz import PrefSetting


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        setup = Command()
        setup.get_transaction().set_sync(False)
        setup.get_transaction().set_record(False)
        setup.execute = lambda: PrefSetting.create('timezone', 'UTC')
        Command.execute_cmd(setup)
        def write(action):
            cmd = Command()
            cmd.get_transaction().set_sync(False)
            cmd.get_transaction().set_record(True)
            cmd.execute = action
            Command.execute_cmd(cmd)
            # Select this test operation explicitly; default selection ties
            # are exercised separately by the unchanged external client.
            search = Search(TransactionLog.SEARCH_TYPE)
            search.add_filter('type', 'undo')
            search.add_order_by('id desc')
            return search.get_sobject()

        def state():
            search = Search('sthpw/note')
            search.add_filters('code', ['UNDO_CONTRACT', 'UNDO_RENAMED'])
            search.add_order_by('code')
            return [(obj.get_code(), obj.get_value('note')) for obj in search.get_sobjects()]

        def apply(command):
            command.get_transaction().set_sync(False)
            command.get_transaction().set_record(False)
            Command.execute_cmd(command)
            return state()

        def insert():
            obj = SearchType.create('sthpw/note')
            obj.set_value('code', 'UNDO_CONTRACT')
            obj.set_value('note', 'before')
            obj.set_value('process', 'publish')
            obj.commit()

        def update():
            obj = Search('sthpw/note')
            obj.add_filter('code', 'UNDO_CONTRACT')
            obj = obj.get_sobject()
            if case.get('rename'):
                obj.set_value('code', 'UNDO_RENAMED')
            obj.set_value('note', 'after')
            obj.commit()

        if case.get('thread'):
            def fresh(code):
                search = Search('sthpw/note'); search.add_filter('code', code)
                return search.get_sobject()
            def thread():
                root = SearchType.create('sthpw/note')
                root.set_value('code', 'THREAD_ROOT'); root.set_value('note', 'Root')
                root.set_value('context', 'publish'); root.set_value('process', 'publish'); root.commit()
                reply = SearchType.create('sthpw/note')
                reply.set_value('code', 'THREAD_REPLY'); reply.set_value('note', 'Reply')
                reply.set_value('context', 'publish'); reply.set_value('process', 'publish')
                reply.set_value('parent_id', root.get_id()); reply.commit()
            write(thread)
            root_id = fresh('THREAD_ROOT').get_id()
            def remove():
                fresh('THREAD_REPLY').delete(); fresh('THREAD_ROOT').delete()
            log = write(remove)
            apply(UndoCmd(transaction_log=log))
            root, reply = fresh('THREAD_ROOT'), fresh('THREAD_REPLY')
            return [root.get_id() == root_id, reply.get_value('parent_id') == root.get_id()]

        log = write(insert)
        result = [state(), apply(UndoCmd(transaction_log=log)), apply(RedoCmd(transaction_log=log))]
        log = write(update)
        result.extend([state(), apply(UndoCmd(transaction_log=log)), apply(RedoCmd(transaction_log=log))])
        def delete():
            search = Search('sthpw/note')
            search.add_filter('code', 'UNDO_RENAMED' if case.get('rename') else 'UNDO_CONTRACT')
            search.get_sobject().delete()
        log = write(delete)
        result.extend([state(), apply(UndoCmd(transaction_log=log)), apply(RedoCmd(transaction_log=log))])
        return result
    finally:
        Environment.set_security(previous)
