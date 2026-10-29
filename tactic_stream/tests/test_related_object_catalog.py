"""Handler's portable schema catalogue matches Stream's related-object reader."""
import ast
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_table_services as fixtures
from pyasm.search import Search
from pyasm.common import Environment
from tactic_stream.server.object_operations import read_relations


class RelatedCatalog(unittest.TestCase):
    setUp = fixtures.TableServices.setUp

    def test_native_catalog_preserves_server_relationships_and_project_guard(self):
        root = Path(os.environ.get('TACTIC_HANDLER_ROOT', Path(__file__).resolve().parents[3] / 'TH'))
        source = root / 'thlib/ui/related_objects.py'
        function = next(node for node in ast.parse(source.read_text(encoding='utf-8')).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'read_related_types')
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
        read = namespace['read_related_types']
        parent = Search.get_by_code('contract/entity', 'A')
        key = parent.get_search_key()
        expected = {row['search_type'] for row in read_relations('contract/entity', key)['relations'] if row['available']}
        result = read(key)
        self.assertTrue(result)
        self.assertEqual({row['command'].split(':', 2)[2] for row in result}, expected)
        with self.assertRaises(ValueError):
            read(key.replace('project=one', 'project=two'))
        security = Environment.get_security()
        with patch.object(security, 'is_admin', return_value=False), patch.object(security, 'is_logged_in', return_value=False):
            with self.assertRaises(PermissionError):
                read(key)


if __name__ == '__main__':
    unittest.main()
