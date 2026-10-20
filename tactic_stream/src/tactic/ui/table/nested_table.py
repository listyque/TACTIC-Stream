"""Transport command for nested tables; values use the normal table projection."""
from pyasm.command import Command
from .nested_scope import read_nested_scope


class NestedTableReadCmd(Command):
    def execute(self):
        from tactic_stream.server.interface import read_interface
        from tactic_stream.server.table_cells import read_table_cells

        result = read_nested_scope(**self.kwargs)
        result['definition'] = read_interface(result['searchType'], result['view'])
        result['cells'] = read_table_cells(result['searchType'], result['view'],
            [record['__search_key__'] for record in result['records']])
        self.info = result
        return result
