"""Project-defined task navigation preserves wildcard/system behavior."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from xml.etree import ElementTree as ET
from tactic_stream.server.result_items import relations, schema_relations


class Navigation(unittest.TestCase):
    def test_only_explicit_native_task_edges_are_exposed(self):
        root = ET.fromstring('''<schema>
          <connect from="sthpw/task" to="*" relationship="search_type"/>
          <connect from="sthpw/task" to="demo/chat" relationship="search_type" title="Tasks"/>
        </schema>''')
        schema = Mock(xml=root, parent_schema=None, sthpw_schema=None)
        schema.get_code.return_value = 'demo'
        schema.get_relationship_attrs.return_value = {'relationship':'search_type'}
        definition = Mock()
        definition.get_record_read_options.return_value = {'available':True}
        definition.get_title.return_value = 'Native tasks'
        definition.get_value.return_value = ''
        with patch('tactic_stream.server.result_items.SearchType.get', return_value=definition):
            self.assertEqual(schema_relations('demo/project',schema), [])
            actual = schema_relations('demo/chat',schema)
            schema.get_code.return_value = 'admin'
            self.assertEqual(schema_relations('demo/chat',schema), [])
        self.assertEqual([(r['search_type'],r['title']) for r in actual], [('sthpw/task','Tasks')])

    def test_shared_records_use_only_their_current_projects_schema(self):
        obj = Mock()
        obj.get_base_search_type.return_value = 'sthpw/task'
        obj.get_value.return_value = 'demo'
        with patch('tactic_stream.server.result_items.Project.get_project_code',return_value='demo'), patch('pyasm.biz.Schema.get') as project_schema, patch('tactic_stream.server.result_items.schema_relations') as describe:
            relations(obj)
            describe.assert_called_with('sthpw/task',project_schema.return_value,'child')
            project_schema.reset_mock()
            obj.get_value.return_value = 'other'
            relations(obj)
            project_schema.assert_not_called()
            describe.assert_called_with('sthpw/task',obj.get_schema.return_value,'child')


if __name__ == '__main__': unittest.main()
