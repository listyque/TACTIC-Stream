"""Shared plain-value vectors and real database scalar round trips."""
import importlib.util
import json
from pathlib import Path
import unittest

from test_foundation import ROOT
import test_raw_database as raw_tests

HANDLER = ROOT.parent.parent / 'th_codex/thlib/ui/admin/raw_cell_values.py'
spec = importlib.util.spec_from_file_location('handler_raw_cell_values', HANDLER)
values = importlib.util.module_from_spec(spec)
spec.loader.exec_module(values)


class RawCellValues(unittest.TestCase):
    def test_shared_valid_and_invalid_vectors(self):
        vectors = json.loads((ROOT / 'tests/fixtures/raw_cell_values.json').read_text(encoding='utf-8'))
        for case in vectors['valid']:
            with self.subTest(case=case):
                result = values.cell_value(case['text'], case['type'], case.get('mode', 'value'))
                self.assertEqual(result, case['value'])
                self.assertIs(type(result), type(case['value']))
        for case in vectors['invalid']:
            with self.subTest(case=case), self.assertRaises(ValueError):
                values.cell_value(case['text'], case['type'], case.get('mode', 'value'))

    def test_strings_are_displayed_without_serialization(self):
        for text in ('plain', 'NULL', '"quoted"', 'line one\nline two', '42', ''):
            self.assertEqual(values.cell_text(text), text)
        self.assertEqual(values.cell_text(None), '')
        self.assertEqual(values.cell_text({'flag': True}), '{"flag":true}')


class RawCellRoundTrips(unittest.TestCase):
    def setUp(self):
        self.fixture = raw_tests.RawDatabaseTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        with self.fixture.store.connection(write=True) as db:
            db.execute('CREATE TABLE raw_cell_types (id INTEGER PRIMARY KEY, text TEXT, number BIGINT, flag BOOLEAN, data JSON)')
            db.execute("INSERT INTO raw_cell_types VALUES (1,'old',7,0,'{}')")

    def test_plain_text_typed_values_json_scalar_and_sql_null_are_distinct(self):
        loaded = self.fixture.request('load', 'raw_cell_types')
        cases = [('text', 'TEXT', 'quotes " \\ line\nЮникод', 'value'),
                 ('number', 'BIGINT', '9223372036854775807', 'value'),
                 ('flag', 'BOOLEAN', 'true', 'value'),
                 ('data', 'JSON', 'null', 'value'), ('data', 'JSON', '"quoted"', 'value'),
                 ('data', 'JSON', '', 'null'), ('text', 'TEXT', '', 'value'),
                 ('text', 'TEXT', 'NULL', 'value'), ('text', 'TEXT', '', 'null')]
        for name, column_type, text, mode in cases:
            row = loaded['document']['rows'][0]
            converted = values.cell_value(text, column_type, mode)
            draft = dict(offset=0, rows=[dict(key=row['key'], revision=row['revision'], values={name: converted})])
            loaded = self.fixture.request('save', 'raw_cell_types', document=draft, expected_revision=loaded['revision'])
            actual = loaded['document']['rows'][0]['values'][name]
            self.assertEqual(actual, int(converted) if name == 'flag' else converted)
