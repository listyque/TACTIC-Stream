"""Column geometry persists through both clients without growing Undo/history."""
from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest

from pyasm.command import Command
from pyasm.common import XmlException
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.widget_configuration import (
    WidgetConfigConflict, read_widget_configuration, save_widget_configuration,
)


XML = ('<config><!--keep--><table layout="TableLayoutWdg">'
       '<element name="code" width="90" title="Code"/>'
       '<element name="name" width="160"><display class="custom.Wdg">'
       '<value> original text </value></display></element></table></config>')


class ColumnWidthHistory(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'data')
        self.store.initialize(hash_password('width-test-password'))
        self.api = Api(self.store)
        self.api.protocol = 'json'
        self.token = self.api.get_ticket('admin', 'width-test-password')
        self.auth = dict(ticket=self.token, project='admin')

    @contextmanager
    def context(self):
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.token)
            yield

    def create(self, xml=XML, view='table'):
        return self.api.dispatch('insert', (self.auth, 'config/widget_config',
            dict(search_type='sthpw/project', view=view, config=xml)), dict(triggers=False))

    def counts(self):
        with self.context():
            return tuple(Search(kind).get_count() for kind in (
                'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp',
                'config/widget_config'))

    def test_native_updates_and_web_saves_keep_widths_without_history(self):
        record = self.create()
        baseline = self.counts()
        timestamp_count = baseline[2]
        for width in range(100, 120):
            xml = XML.replace('width="90"', 'width="%d"' % width)
            saved = self.api.dispatch('insert_update', (
                self.auth, record['__search_key__'], dict(config=xml)), dict(triggers=False))
            self.assertEqual(saved['config'], xml)
            counts = self.counts()
            self.assertEqual(counts[:2], baseline[:2])
            if width == 100:
                timestamp_count = counts[2]
            self.assertEqual(counts[2:], (timestamp_count, baseline[3]))
        baseline = self.counts()
        with self.context():
            state = read_widget_configuration('sthpw/project', 'table')
            saved = save_widget_configuration('sthpw/project', 'table', record['id'],
                XML.replace('width="90"', 'width="240"'), state['revision'])
            self.assertIn('width="240"', saved['sources'][0]['xml'])
            with self.assertRaises(WidgetConfigConflict):
                save_widget_configuration('sthpw/project', 'table', record['id'], XML,
                    state['revision'])
        self.assertEqual(self.counts(), baseline)
        stored = self.api.dispatch('query', (self.auth, 'config/widget_config', [['id', record['id']]]))
        self.assertIn('width="240"', stored[0]['config'])

    def test_material_changes_still_have_history(self):
        first = '<element name="code" width="90" title="Code"/>'
        changes = [
            XML.replace('title="Code"', 'title="Renamed"'),
            XML.replace('<!--keep-->', '<!--changed-->'),
            XML.replace(' original text ', 'original text'),
            XML.replace('custom.Wdg', 'custom.OtherWdg'),
            XML.replace('name="code"', 'name="other"'),
            XML.replace('<element name="code"', '<element name="code" th_hide_order="1"'),
            XML.replace('</table>', '<element name="extra"/></table>'),
            XML.replace('<display class="custom.Wdg">', '<display class="custom.Wdg" width="20">'),
            XML.replace(first, '').replace('</table>', first + '</table>'),
        ]
        for xml in changes:
            with self.subTest(xml=xml):
                record = self.create()
                before = self.counts()
                self.api.dispatch('update', (self.auth, record['__search_key__'], dict(
                    config=xml.replace('width="90"', 'width="250"'))))
                after = self.counts()
                self.assertGreater(after[0], before[0])
                self.assertGreater(after[1], before[1])
        for view, xml in (
            ('definition', XML.replace('table', 'definition')),
            ('table', XML.replace('TableLayoutWdg', 'ItemLayoutWdg')),
        ):
            with self.subTest(view=view, xml=xml):
                record = self.create(xml, view)
                before = self.counts()
                self.api.dispatch('update', (self.auth, record['__search_key__'],
                    dict(config=xml.replace('width="90"', 'width="250"'))))
                self.assertGreater(self.counts()[1], before[1])

    def test_named_views_ignore_formatting_but_keep_literal_spaces(self):
        xml = XML.replace('<table layout="TableLayoutWdg">',
            '<view name="table@preset">').replace('</table>', '</view>')
        record = self.create(xml, 'table@preset')
        before = self.counts()
        resized = xml.replace('width="90"', 'width="250"').replace(
            '<element name="code"', '\n  <element name="code"')
        self.api.dispatch('update', (self.auth, record['__search_key__'], dict(config=resized)))
        self.assertEqual(self.counts()[:2], before[:2])
        spaces = resized.replace(' original text ', ' ')
        self.api.dispatch('update', (self.auth, record['__search_key__'], dict(config=spaces)))
        before = self.counts()
        self.api.dispatch('update', (self.auth, record['__search_key__'],
            dict(config=spaces.replace('<value> </value>', '<value/>'))))
        self.assertGreater(self.counts()[1], before[1])

    def test_quiet_update_still_validates_authorizes_and_rolls_back(self):
        record = self.create()
        before = self.counts()
        with self.assertRaises(XmlException):
            self.api.dispatch('update', (self.auth, record['__search_key__'], dict(config='<broken>')))
        with self.context():
            command = Command()
            def fail():
                item = Search.get_by_search_key(record['__search_key__'])
                item.set_value('config', XML.replace('width="90"', 'width="250"'))
                item.commit()
                raise ValueError('rollback width')
            command.execute = fail
            with self.assertRaisesRegex(ValueError, 'rollback width'):
                Command.execute_cmd(command)
        self.assertEqual(self.counts(), before)
        stored = self.api.dispatch('query', (self.auth, 'config/widget_config', [['id', record['id']]]))
        self.assertEqual(stored[0]['config'], XML)
        self.api.dispatch('insert', (self.auth, 'sthpw/login', dict(login='width_reader',
            code='width_reader', password=hash_password('width-reader-password'))))
        token = self.api.get_ticket('width_reader', 'width-reader-password')
        with self.assertRaises(SecurityException):
            self.api.dispatch('update', (dict(ticket=token, project='admin'),
                record['__search_key__'], dict(config=XML.replace('width="90"', 'width="250"'))))


if __name__ == '__main__':
    unittest.main()
