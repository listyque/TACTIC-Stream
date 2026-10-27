"""Native agent item views: real MCP, revision conflicts, replay and cross-type cards."""
import asyncio
from pathlib import Path
import unittest
from uuid import uuid4

from mcp import Client
from tactic_stream.admin_agent import StreamConnection, create_server
import test_transport


class AgentItemLayouts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.url = test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_native_definition_read_uses_viewer_acl_without_python_execution(self):
        from xmlrpc.client import Fault
        with test_transport.Transport.store.connection(write=True) as database:
            database.execute("INSERT INTO login(code,login,password) SELECT 'layout_viewer','layout_viewer',password FROM login WHERE login='admin'")
            rules = '<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="contract/entity" access="view"/></rules>'
            database.execute('INSERT INTO login_group(code,login_group,access_rules) VALUES(?,?,?)', ('layout_readers', 'layout_readers', rules))
            database.execute("INSERT INTO login_in_group(code,login,login_group) VALUES('layout_reader','layout_viewer','layout_readers')")
        with test_transport.Transport.proxy(self) as proxy:
            admin = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one')
            command = 'tactic.ui.panel.item_layout_cmd.ItemLayoutCmd'
            state = proxy.execute_cmd(admin, command, dict(action='read', project_code='one', search_type='contract/entity', view='viewer_cards'))['info']
            xml = '<config><viewer_cards layout="sobject-layout"><element name="name"><display class="title"><bind>record.code</bind></display></element></viewer_cards></config>'
            proxy.execute_cmd(admin, command, dict(action='apply', project_code='one', search_type='contract/entity', view='viewer_cards',
                xml=xml, source_id=None, expected_revision=state['revision'], operation_id=str(uuid4())))
            viewer = dict(ticket=proxy.get_ticket('layout_viewer', 'private-test-password'), project='one')
            read = 'tactic.ui.table.NestedTableReadCmd'
            result = proxy.execute_cmd(viewer, read, dict(search_type='contract/entity', view='viewer_cards', definition_only=True))['info']
            self.assertEqual(result['definition']['table']['item_layout']['elements'][0]['options']['bind'], 'record.code')
            self.assertNotIn('records', result)
            with self.assertRaises(Fault):
                proxy.execute_cmd(viewer, command, dict(action='read', project_code='one', search_type='contract/entity', view='viewer_cards'))
            with self.assertRaises(Fault):
                proxy.execute_cmd(dict(viewer, project='two'), read, dict(search_type='contract/entity', view='viewer_cards', definition_only=True))

    def test_real_tools_save_reusable_type_card_and_recover_receipt(self):
        with test_transport.Transport.proxy(self) as proxy:
            ticket = proxy.get_ticket('admin', 'private-test-password')

        async def run():
            connection = StreamConnection(self.url, 'one', ticket)
            server = create_server(connection, Path(__file__).resolve().parents[1], allow_page_save=True)
            async with Client(server) as client:
                async def call(name, **values):
                    result = await client.call_tool('ts_item_layout_' + name, values)
                    self.assertFalse(result.is_error, str(result.content))
                    return result.structured_content

                state = await call('read', search_type='sthpw/task', view='agent_task_card')
                xml = '<config><agent_task_card layout="sobject-layout"><element name="task_title"><display class="title"><bind>record.process</bind></display></element></agent_task_card></config>'
                payload = dict(search_type='sthpw/task', view='agent_task_card', xml=xml,
                               expected_revision=state['revision'], operation_id=str(uuid4()))
                preview = await call('preview', **{k: v for k, v in payload.items() if k != 'operation_id'})
                self.assertEqual(preview['interface']['table']['item_layout']['elements'][0]['kind'], 'title')
                saved = await call('save', **payload)
                self.assertEqual(await call('save', **payload), saved)
                self.assertEqual(await call('operation', operation_id=payload['operation_id']), saved)
                bad = await client.call_tool('ts_item_layout_save', dict(payload, xml=xml.replace('process', 'status')))
                self.assertTrue(bad.is_error)
                stale = await client.call_tool('ts_item_layout_save', dict(payload, operation_id=str(uuid4())))
                self.assertTrue(stale.is_error)
                root = await call('read', search_type='contract/entity', view='agent_item_tree')
                composed = '<config><agent_item_tree layout="sobject-layout" collection="tree"><element name="task" search_type="sthpw/task"><display class="view"><view>agent_task_card</view></display></element></agent_item_tree></config>'
                preview = await call('preview', search_type='contract/entity', view='agent_item_tree',
                                     xml=composed, expected_revision=root['revision'])
                child = preview['interface']['table']['item_layout']['elements'][0]
                self.assertEqual(child['search_type'], 'sthpw/task')
                self.assertEqual(child['widget_layout']['elements'][0]['options']['bind'], 'record.process')
                invalid = await client.call_tool('ts_item_layout_preview', dict(search_type='contract/entity', view='agent_item_tree',
                    xml=composed.replace('sthpw/task', 'sthpw/task?project=two'), expected_revision=root['revision']))
                self.assertTrue(invalid.is_error)

        asyncio.run(run())
