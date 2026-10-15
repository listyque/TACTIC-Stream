"""Wide TEL roots and mutable, inherited schema lookup contracts."""
from pathlib import Path
import tempfile
import unittest

from test_foundation import fixture
from test_schema import relationship_fixture
from pyasm.biz import ExpressionParser, Schema
from pyasm.search import Search, SearchKey
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


class CountingRoots(list):
    serializations = 0

    def __str__(self):
        self.serializations += 1
        return super().__str__()


class RelationPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.store = Store(Path(cls.temporary.name))
        cls.store.initialize(hash_password('private-relation-check'))
        fixture(cls.store)
        relationship_fixture(cls.store)
        cls.api = Api(cls.store)
        cls.ticket = cls.api.get_ticket('admin', 'private-relation-check')

    def test_tel_wide_roots_preserve_values_and_object_cache(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            first = Search.get_by_code('contract/entity', 'A')
            second = Search.get_by_code('contract/entity', 'B')
            roots = CountingRoots([first, second] * 64)
            parser = ExpressionParser()
            self.assertEqual(parser.eval('@GET(.name)', roots), ["Первый", "O'Reilly"] * 64)
            self.assertLessEqual(roots.serializations, 2)
            cache = parser.get_cache_sobjects()
            self.assertEqual(cache[first], 'Первый')
            self.assertEqual(cache[SearchKey.get_by_sobject(first)], 'Первый')
            first.set_value('name', 'Changed in the same request')
            self.assertEqual(parser.eval('@GET(.name)', first, single=True, use_cache=False),
                             'Changed in the same request')

    def test_tel_batch_relations_preserve_paths_leaves_and_cache(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            first = Search.get_by_code('contract/entity', 'A')
            second = Search.get_by_code('contract/entity', 'B')
            roots = CountingRoots([first, second] * 64)
            parser = ExpressionParser()
            self.assertEqual(parser.eval('@GET(contract/child.code)', roots), ['CH1', 'CH2'])
            self.assertLessEqual(roots.serializations, 3)
            cache = parser.get_cache_sobjects()
            self.assertEqual([obj.get_code() for obj in cache[first.get_search_key()]], ['CH1', 'CH2'])
            self.assertEqual(cache[second.get_search_key()], [])
            self.assertEqual(parser.eval('@GET(alternate:contract/child.code)', first),
                             ['CH2', 'CH4', 'CH5'])

    def test_schema_index_preserves_priority_drafts_and_uncached_reads(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            schema = Schema.get()
            self.assertEqual(schema.get_relationship_attrs('contract/tag', 'contract/entity')['path'], 'last')
            self.assertEqual(schema.get_relationship_attrs('contract/tag', 'contract/entity', path='first')['from_col'],
                             'first_entity')
            self.assertEqual(schema.get_relationship_attrs('contract/child', 'contract/entity', type='hierarchy')['from_col'],
                             'entity_code')
            self.assertEqual(schema.get_relationship_attrs('contract/ref', 'contract/entity')['relationship'], 'search_type')
            schema.edit_connection('contract/old_child', 'contract/entity', commit=False)
            self.assertEqual(schema.get_relationship_attrs('contract/old_child', 'contract/entity'), {})
            schema.add_search_type('contract/old_child', parent_type='contract/entity', commit=False)
            self.assertEqual(schema.get_relationship_attrs('contract/old_child', 'contract/entity')['from_col'], 'entity_code')
            xml = schema.get_xml()
            node = xml.get_node("schema/connect[@from='contract/child'][@type='hierarchy']")
            xml.set_attribute(node, 'from_col', 'alternate_entity_code')
            self.assertEqual(schema.get_relationship_attrs('contract/child', 'contract/entity', cache=False)['from_col'],
                             'alternate_entity_code')
            schema.set_xml(xml.to_string())
            self.assertEqual(schema.get_relationship_attrs('contract/child', 'contract/entity')['from_col'],
                             'alternate_entity_code')
            schema.xml.remove(next(node for node in schema.xml.findall('connect')
                                   if node.get('from') == 'contract/old_child'))
            schema.relationships.clear()
            self.assertEqual(schema.get_relationship_attrs('contract/old_child', 'contract/entity'), {})

    def test_inherited_cache_is_reused_and_parent_edits_remain_visible(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            schema = Schema.get()
            parent = schema.parent_schema
            pair = ('contract/inherited', 'contract/entity')
            first = schema.get_relationship_attrs(*pair)
            self.assertIs(first, schema.get_relationship_attrs(*pair))
            self.assertTrue(parent.relationships)
            parent.edit_connection(*pair, commit=False)
            self.assertEqual(schema.get_relationship_attrs(*pair), {})
            parent.add_search_type(pair[0], parent_type=pair[1], commit=False)
            self.assertEqual(schema.get_relationship_attrs(*pair)['from_col'], 'entity_code')

