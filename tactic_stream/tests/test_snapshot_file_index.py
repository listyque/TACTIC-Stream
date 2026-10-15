import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from pyasm.biz import Snapshot
from pyasm.common import Common, Container, Xml
from pyasm.common.lxml_wrapper import XmlException
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


class SnapshotFileIndex(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = Store(Path(self.directory.name) / 'data')
        self.store.initialize(hash_password('private-index-test'))
        self.api = Api(self.store)
        self.ticket = self.api.get_ticket('admin', 'private-index-test')
        scope = request_context(RequestContext(self.store, 'admin', 'admin'))
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.api.auth.bind_security('admin', self.ticket)
        self.snapshot = Snapshot()
        self.snapshot.set_value('code', 'INDEX_TEST')

    def test_thousand_files_require_one_parse_for_repeated_lookups(self):
        source = '<snapshot>' + ''.join('<file name="file%d" file_code="F%d" type="part%d" use_naming="false"/>' %
                                      (index, index, index) for index in range(1000)) + '</snapshot>'
        self.snapshot.set_value('snapshot', source)
        read_string = Xml.read_string
        with patch.object(Xml, 'read_string', autospec=True, side_effect=read_string) as parsing:
            for index in range(1000):
                self.assertEqual(self.snapshot.get_type_by_file_name('file%d' % index), 'part%d' % index)
                self.assertEqual(self.snapshot.get_type_by_file_code('F%d' % index), 'part%d' % index)
                self.assertFalse(self.snapshot.get_use_naming_by_type('part%d' % index))
            self.assertEqual(parsing.call_count, 1)

    def test_duplicates_missing_attributes_and_empty_values_keep_xml_selection(self):
        source = '''<snapshot>
<file name="same" file_code="F1" type="main"/>
<file name="same" file_code="F1" type="other"/>
<file name="second" file_code="F2" type="main" use_naming="false"/>
<file name="third" file_code="F3" type="main" use_naming="true"/>
<file/><file name="" file_code="" type="" use_naming=""/>
<file name="missing_type"/><file name="missing_type" type="later"/>
</snapshot>'''
        self.snapshot.set_value('snapshot', source)
        xml = self.snapshot.get_snapshot_xml()
        self.assertEqual(self.snapshot.get_type_by_file_name('same'), 'main')
        self.assertEqual(self.snapshot.get_type_by_file_code('F1'), 'main')
        self.assertIsNone(self.snapshot.get_type_by_file_name('missing_type'))
        self.assertEqual(self.snapshot.get_type_by_file_name(''), '')
        for kind in ('main', 'other', '', 'unknown'):
            expected = xml.get_value("snapshot/file[@type='%s']/@use_naming" % kind) != 'false'
            self.assertEqual(self.snapshot.get_use_naming_by_type(kind), expected)
        self.assertEqual(self.snapshot.get_type_by_file_code('missing'), '')
        # Direct attribute lookup also handles quotes without constructing XPath.
        self.snapshot.set_value('snapshot', '<snapshot><file name="a&amp;b&apos;&quot;" file_code="F&apos;&quot;" type="main&apos;&quot;" use_naming="false"/></snapshot>')
        self.assertEqual(self.snapshot.get_type_by_file_name('a&b\'"'), 'main\'"')
        self.assertEqual(self.snapshot.get_type_by_file_code('F\'"'), 'main\'"')
        self.assertFalse(self.snapshot.get_use_naming_by_type('main\'"'))

    def test_updates_compressed_xml_and_row_refresh_rebuild_the_index(self):
        first = '<snapshot><file name="first" file_code="F" type="main"/></snapshot>'
        second = '<snapshot><file name="second" file_code="F" type="image" use_naming="false"/></snapshot>'
        self.snapshot.set_value('snapshot', first)
        self.assertEqual(self.snapshot.get_type_by_file_name('first'), 'main')
        self.snapshot.set_value('snapshot', Common.compress_transaction(second))
        self.assertEqual(self.snapshot.get_type_by_file_name('first'), '')
        self.assertEqual(self.snapshot.get_type_by_file_code('F'), 'image')
        self.assertFalse(self.snapshot.get_use_naming_by_type('image'))
        self.snapshot.set_update_data({})
        self.snapshot.has_updates = False
        self.snapshot.set_data(dict(self.snapshot.data, code='INDEX_TEST', snapshot=first))
        self.assertEqual(self.snapshot.get_type_by_file_code('F'), 'main')

    def test_mutable_xml_stays_fresh_and_external_cache_is_honored(self):
        source = '<snapshot><file name="original" file_code="F" type="main"/></snapshot>'
        self.snapshot.set_value('snapshot', source)
        self.assertEqual(self.snapshot.get_type_by_file_name('original'), 'main')
        edited = self.snapshot.get_snapshot_xml()
        node = edited.get_node('snapshot/file')
        Xml.set_attribute(node, 'type', 'image')
        self.assertEqual(self.snapshot.get_type_by_file_name('original'), 'main')
        self.assertEqual(self.snapshot.get_snapshot_xml().get_value('snapshot/file/@type'), 'main')
        cache = Container.get_full_dict('SObject:xml_cache')
        key = self.snapshot.get_search_key() + '|snapshot'
        cache[key] = edited
        self.assertEqual(self.snapshot.get_type_by_file_name('original'), 'image')
        Xml.set_attribute(node, 'type', 'changed')
        Xml.set_attribute(node, 'use_naming', 'false')
        self.assertEqual(self.snapshot.get_type_by_file_code('F'), 'changed')
        self.assertFalse(self.snapshot.get_use_naming_by_type('changed'))
        del cache[key]
        self.assertEqual(self.snapshot.get_type_by_file_code('F'), 'main')

    def test_request_boundary_and_invalid_xml_do_not_reuse_cached_values(self):
        self.snapshot.set_value('snapshot', '<snapshot><file name="first" type="main"/></snapshot>')
        read_string = Xml.read_string
        with patch.object(Xml, 'read_string', autospec=True, side_effect=read_string) as parsing:
            self.assertEqual(self.snapshot.get_type_by_file_name('first'), 'main')
            with request_context(RequestContext(self.store, 'admin', 'admin')):
                self.api.auth.bind_security('admin', self.ticket)
                self.assertEqual(self.snapshot.get_type_by_file_name('first'), 'main')
            self.assertEqual(parsing.call_count, 2)
        self.snapshot.set_value('snapshot', '<!DOCTYPE snapshot><snapshot/>')
        with self.assertRaises(XmlException):
            self.snapshot.get_type_by_file_name('first')
        self.snapshot.set_value('snapshot', '<snapshot>')
        with self.assertLogs('pyasm.search.search', level='WARNING'):
            self.assertEqual(self.snapshot.get_type_by_file_name('first'), '')
