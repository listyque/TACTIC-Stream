"""No-record Item layout editing against a private database and real browser."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from uuid import uuid4


class LayoutSampleBrowser(unittest.TestCase):
    def test_empty_and_selected_scope_samples_do_not_create_records(self):
        from test_transport import Transport
        from tactic_stream.server.api import Api

        class Fixture(Transport):
            pass

        Fixture.setUpClass()
        self.addCleanup(Fixture.tearDownClass)
        with Fixture.store.connection('one',write=True) as db:
            db.execute('DELETE FROM collection')
        api=Api(Fixture.store)
        api.protocol='json'
        auth=dict(ticket=api.get_ticket('admin','private-test-password'),project='one')
        child_xml='<config><empty_card layout="sobject-layout"><element name="title" height="40"><display class="title"><bind>record.name</bind></display></element><element name="progress" row="2"><display class="field"><bind>record.amount</bind><format>progress</format></display></element></empty_card></config>'
        parent_xml='<config><mixed_cards layout="sobject-layout"><element name="title"><display class="title"><bind>record.name</bind></display></element><element name="collection" search_type="contract/collection" row="2"><display class="view"><view>empty_card</view></display></element></mixed_cards></config>'
        for search_type,view,xml in [('contract/collection','empty_card',child_xml),('contract/entity','mixed_cards',parent_xml)]:
            api.dispatch('insert',(auth,'config/widget_config',dict(search_type=search_type,view=view,config=xml)))
        def call(action,**values):
            return api.dispatch('execute_cmd',(auth,'tactic.ui.panel.dashboard_cmd.DashboardCmd',dict(action=action,project_code='one',**values)))['info']
        call('apply',document=dict(name='work',title='Work',blocks=[dict(kind='items',search_type='contract/entity',view='mixed_cards')]),expected_revision=call('read')['revision'],operation_id=str(uuid4()))
        root=Path(__file__).resolve().parents[1]
        output=root/'.screenshots/layout-sample-data'
        output.mkdir(parents=True,exist_ok=True)
        with (output/'browser.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([shutil.which('node'),'tests/layout_sample_data_browser.mjs',Fixture.url,str(output)],cwd=root/'frontend',
                env=dict(os.environ,PLAYWRIGHT_BROWSERS_PATH=str(root/'.browser-cache')),stdout=log,stderr=subprocess.STDOUT,timeout=120)
        self.assertEqual(result.returncode,0,(output/'browser.log').read_text(encoding='utf-8'))
        with Fixture.store.connection('one') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM collection').fetchone()[0],0)
        records=api.dispatch('query',(auth,'config/widget_config'),dict(filters=[('search_type','contract/collection'),('view','empty_card')]))
        saved=records[0]['config']
        self.assertNotIn('Example item',saved)
        self.assertNotIn('Example value',saved)
        self.assertNotEqual(saved,child_xml)
