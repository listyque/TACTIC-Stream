"""Compare the Qt-free adaptation with the current Handler's pure AST logic."""
from pathlib import Path
import unittest

from tactic_stream.server import script_features as features


class ScriptFeatures(unittest.TestCase):
    def test_completion_starts_at_the_cursor_after_a_newline(self):
        for source in ('pri\n', 'server.que\n', 'pri\r\n'):
            with self.subTest(source=source):
                self.assertEqual(features.completion_items(source, len(source)), [])
                self.assertTrue(all(row['start'] == len(source) for row in features.completion_items(source, len(source), True)))

    def test_native_outline_completion_and_no_execution(self):
        path = Path('D:/code/th_codex/thlib/ui/script_editor_features.py')
        native = path.read_text(encoding='utf-8')
        namespace = dict(features.__dict__, __file__=str(path))
        functions = native[native.index('def _node_signature('):native.index('def find_matches(')]
        exec(compile(functions, str(path), 'exec'), namespace)
        source = '''"""class Fake: ignored docstring"""
import json as data
class Worker:
    def __init__(self):
        self.value = 1
    async def work(self, name="demo"):
        """Run a job."""
        return self.value
    def next(self):
        return self.wo
'''
        symbols = features.document_symbols(source)
        self.assertEqual(symbols, namespace['document_symbols'](source))
        self.assertEqual([row['qualifiedName'] for row in symbols], ['Worker', 'Worker.__init__', 'Worker.work', 'Worker.next'])
        for text in (source, 'import json as data\ndata.du', 'def hello(name="world"):\n    pass\nhel', 'pr', 'def good():\n    pass\ndef unfinished('):
            self.assertEqual(features.completion_items(text, len(text), True), namespace['completion_items'](text, len(text), True))
            self.assertEqual(features.document_symbols(text), namespace['document_symbols'](text))
        item = features.completion_items(source, len(source.rstrip()), True)[0]
        self.assertEqual(item['insertText'], 'work()')
        self.assertEqual(item['cursorOffset'], -1)
        self.assertIn('async (self, name=', item['detail'])
        self.assertIn('Run a job.', item['detail'])
        self.assertEqual(features._imported_display_names(source), ('data',))
        self.assertFalse(features.completion_items('p', 1, False))
        server = features.completion_items('server.que', 10, True)
        self.assertEqual(server[0]['label'], 'query')
        self.assertIn('search_type', server[0]['detail'])
        self.assertIsNone(features._module_source_path('../private'))
        # Parsing imports/calls must not execute them or alter the process.
        self.assertEqual(features.document_symbols('raise RuntimeError("must not run")'), [])
        self.assertIsNone(features._safe_tree('[' * 4000))


if __name__ == '__main__':
    unittest.main()
