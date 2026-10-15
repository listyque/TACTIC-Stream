"""Unchanged command script on source TACTIC and native database vendors."""
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security
from tactic.ui.panel.collection_wdg import CollectionAddCmd, CollectionRemoveCmd, CollectionDeleteCmd


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        prefix = 'CB_' if self.operation == 'batch_cycle' else 'CC_'
        kind = 'contract/collect?project=' + self.project
        nodes = {}
        for code, is_collection in (('ROOT', True), ('SUB', True), ('OTHER', True), ('LEAF', False)):
            obj = SearchType.create(kind)
            obj.set_value('code', prefix + code)
            obj.set_value('name', prefix + code)
            obj.set_value('_is_collection', is_collection)
            obj.commit()
            nodes[code] = obj
        root, sub, other, leaf = [nodes[code] for code in ('ROOT', 'SUB', 'OTHER', 'LEAF')]
        add = CollectionAddCmd(collection_keys=[root.get_search_key()], search_keys=[sub.get_search_key(), leaf.get_search_key()])
        Command.execute_cmd(add)
        again = CollectionAddCmd(collection_keys=[root.get_search_key()], search_keys=[leaf.get_search_key()])
        Command.execute_cmd(again)
        if self.operation == 'batch_cycle':
            cmd = CollectionAddCmd(collection_keys=[other.get_search_key(), sub.get_search_key()], search_keys=[root.get_search_key()])
            Command.execute_cmd(cmd)
            links = Search('contract/collect_in_collect')
            links.add_filter('parent_code', other.get_code())
            return {'message': cmd.get_info()['message'], 'earlier_destination_edges': links.get_count()}
        remove = CollectionRemoveCmd(collection_key=root.get_search_key(), search_keys=[leaf.get_search_key()])
        Command.execute_cmd(remove)
        nested = CollectionAddCmd(collection_keys=[sub.get_search_key()], search_keys=[leaf.get_search_key()])
        Command.execute_cmd(nested)
        delete = CollectionDeleteCmd(collection_key=sub.get_search_key())
        Command.execute_cmd(delete)
        deleted_cached = Search.get_by_code(kind, sub.get_code()) is not None
        deleted = Search(kind)
        deleted.add_filter('code', sub.get_code())
        assert deleted.get_count() == 0
        assert Search.get_by_code(kind, leaf.get_code()) is not None
        links = Search('contract/collect_in_collect')
        links.add_op('begin')
        links.add_filter('parent_code', sub.get_code())
        links.add_filter('search_code', sub.get_code())
        links.add_op('or')
        assert links.get_count() == 0
        return {'add': add.get_info(), 'again': again.get_info(), 'nested': nested.get_info(),
                'descriptions': [cmd.get_description() for cmd in (add, again, remove, nested, delete)],
                'leaf_collections': [obj.get_code() for obj in leaf.get_collections()],
                'deleted_cached': deleted_cached}


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        cmd = Run()
        cmd.project = case.get('project', 'one')
        cmd.operation = case.get('operation', 'lifecycle')
        return Command.execute_cmd(cmd)
    finally:
        Environment.set_security(previous)
