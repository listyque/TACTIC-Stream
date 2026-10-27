"""Workflow display uses registry colors without rewriting pipeline colors."""
import unittest
import test_transport


class WorkflowCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.url = test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_saved_type_color_reaches_native_workflow_metadata(self):
        with test_transport.Transport.proxy(self) as proxy:
            auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'),
                        project='one')
            command = 'tactic.ui.panel.search_types_cmd.SearchTypesCmd'
            read = proxy.execute_cmd(auth, command, dict(
                action='load', project_code='one',
                identity='contract/entity'))['info']
            document = dict(read['document'], title='Contract entities',
                            color='#9bad77')
            proxy.execute_cmd(auth, command, dict(
                action='save', project_code='one', identity='contract/entity',
                document=document, expected_revision=read['revision']))
            result = proxy.execute_cmd(
                auth, 'tactic.ui.panel.workflow_cmd.WorkflowCmd',
                dict(action='list', project_code='one'))['info']
            self.assertEqual(next(
                row['color'] for row in result['metadata']['searchTypes']
                if row['identity'] == 'contract/entity'), '#9bad77')
