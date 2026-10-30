"""Read-only legacy facts through the real authenticated class-method API."""
from datetime import datetime
import json
import ast
import os
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from pyasm.common import Config, Environment
from pyasm.common.errors import SecurityException
from pyasm.search.storage import Store
from pyasm.search.sql import Sql
from tactic_stream.server.api import Api
from tactic.ui.app.system_info_wdg import SystemInfoWdg
from tools.checkin_benchmark import prepare

CLASS = 'tactic.ui.app.system_info_wdg.SystemInfoWdg'


class SystemInfoTests(unittest.TestCase):
    def test_permission_precedes_all_probes(self):
        for security in (None, Mock(is_admin=lambda: False)):
            with self.subTest(security=security), patch.object(Environment, 'get_security', return_value=security), \
                    patch('platform.uname', side_effect=AssertionError('Must not inspect host')):
                with self.assertRaises(SecurityException):
                    SystemInfoWdg.get_info()
                for operation in (SystemInfoWdg.connection_probe, SystemInfoWdg.performance_probe,
                                  SystemInfoWdg.get_links, lambda: SystemInfoWdg.run_test('email')):
                    with self.assertRaises(SecurityException): operation()

    def test_authenticated_api_is_read_only_and_omits_secrets(self):
        with tempfile.TemporaryDirectory(prefix='system-info-') as temporary, patch.dict(os.environ, {
                'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': '',
                'PRIVATE_SYSTEM_INFO_SECRET': 'never-show-this-secret'}):
            Config.reload_config()
            self.addCleanup(Config.reload_config)
            store = Store(Path(temporary) / 'data')
            api, ticket = prepare(store)
            auth = dict(ticket=ticket, project='one')
            guard = patch.object(Sql, '_do_update', side_effect=AssertionError('Read must not write'))
            writes = guard.start()
            self.addCleanup(guard.stop)
            for class_name,project in ((CLASS,'one'), ('tactic.ui.app.SystemInfoWdg','one'), (CLASS,'admin')):
                result = Api(store).dispatch('execute_class_method', (dict(auth,project=project), class_name, 'get_info', {}),
                    environ={'HTTP_USER_AGENT': 'SystemInfo fixture'})
                sections = {section['title']: section['fields'] for section in result['sections']}
                server = dict(sections['Server'])
                self.assertEqual(server['OS'], platform.system())
                self.assertEqual(dict(sections['Client'])['TACTIC User'], 'admin')
                self.assertEqual(dict(sections['Client'])['User Agent'], 'SystemInfo fixture')
                self.assertIsNotNone(datetime.fromisoformat(server['Server time (UTC)']).utcoffset())
                self.assertIn('Asset Folders', sections)
                self.assertNotIn('never-show-this-secret', json.dumps(result))
                self.assertNotIn(ticket, json.dumps(result))
                self.assertNotIn('private-benchmark-password', json.dumps(result))
            writes.assert_not_called()
            guard.stop()
            with self.assertRaises(Exception):
                Api(store).dispatch('execute_class_method', (dict(auth, ticket='invalid'), CLASS, 'get_info', {}))
            with self.assertRaises(TypeError):
                Api(store).dispatch('execute_class_method', (auth, CLASS, 'get_info', {'path': 'anything'}))

    def test_original_mail_script_cache_and_probe_actions(self):
        with tempfile.TemporaryDirectory(prefix='system-info-actions-') as temporary, patch.dict(os.environ, {
                'TACTIC_CONFIG_PATH':'','TACTIC_TMP_CONFIG_PATH':''}):
            Config.reload_config(); self.addCleanup(Config.reload_config)
            store=Store(Path(temporary)/'data'); api,ticket=prepare(store)
            auth=dict(ticket=ticket,project='one')
            def call(method,**values): return Api(store).dispatch('execute_class_method',(auth,CLASS,method,values))
            self.assertGreater(call('performance_probe')['columns'],0)
            self.assertIn('pid',call('connection_probe'))
            self.assertIsInstance(call('get_links',include_internal=True),list)
            def records(value): return ast.literal_eval(value) if isinstance(value,str) else value
            definitions=records(api.dispatch('query',(auth,'config/widget_config'),{'filters':[('search_type','SideBarWdg'),('view','definition')]}))
            xml='<config><definition><element name="system_fixture" title="Fixture Shots"><display class="pyasm.widget.LinkWdg"><search_type>cg/shot</search_type><view>table</view></display></element></definition></config>'
            if definitions: api.dispatch('update',(auth,definitions[0]['__search_key__'],{'config':xml}))
            else: api.dispatch('insert',(auth,'config/widget_config',dict(search_type='SideBarWdg',view='definition',config=xml)))
            self.assertTrue(any(row['name']=='system_fixture' for row in call('get_links')))
            self.assertEqual(call('resolve_link',name='system_fixture')['search_type'],'cg/shot')
            with self.assertRaises(LookupError): call('resolve_link',name='not-a-real-page')
            with self.assertRaises(ValueError): call('get_links',include_internal='yes')
            original=Config.get_value
            def setting(section,key,*args,**kwargs):
                return 'mail.fixture.invalid' if (section,key)==('services','mailserver') else original(section,key,*args,**kwargs)
            with patch.object(Config,'get_value',side_effect=setting), patch('smtplib.SMTP') as smtp:
                self.assertEqual(call('run_test',action='email',values={'sender':'from@example.invalid','recipients':'to@example.invalid'})['message'],'Email sent successfully')
                smtp.assert_called_once_with('mail.fixture.invalid',25,timeout=30)
                smtp.return_value.sendmail.assert_called_once()
                with self.assertRaises(ValueError): call('run_test',action='email',values={'sender':'from@example.invalid\r\nBcc: other@example.invalid','recipients':'to@example.invalid'})
                self.assertEqual(smtp.call_count,1)
            code="from pyasm.search import Search\nitem=Search.get_by_code('cg/shot','SH001')\nitem.set_value('description','System Info fixture')\nitem.commit()"
            api.dispatch('insert',(auth,'config/custom_script',dict(folder='tests',title='probe',language='python',script=code)))
            self.assertEqual(call('run_test',action='script',values={'path':'tests/probe'})['message'],'Script completed')
            rows=api.dispatch('query',(auth,'cg/shot'))
            rows=ast.literal_eval(rows) if isinstance(rows,str) else rows
            self.assertEqual(rows[0]['description'],'System Info fixture')
            bad=code.replace('System Info fixture','must roll back')+"\nraise ValueError('fixture failure')"
            api.dispatch('insert',(auth,'config/custom_script',dict(folder='tests',title='bad_probe',language='python',script=bad)))
            with self.assertRaisesRegex(ValueError,'fixture failure'): call('run_test',action='script',values={'path':'tests/bad_probe'})
            self.assertEqual(records(api.dispatch('query',(auth,'cg/shot')))[0]['description'],'System Info fixture')
            base=Path(temporary)/'owned-temp'; cache=base/'cache/side_bar'
            cache.mkdir(parents=True);(cache/'fixture').write_text('regenerable cache')
            sibling=base/'cache/keep';sibling.write_text('keep')
            with patch.object(Environment,'get_tmp_dir',return_value=str(base)):
                call('run_test',action='clear_sidebar',values={})
                self.assertFalse(cache.exists());self.assertTrue(sibling.exists())
                cache.write_text('not a directory')
                with self.assertRaises(ValueError): call('run_test',action='clear_sidebar',values={})
                cache.unlink()
                with self.assertRaises(ValueError): call('run_test',action='clear_sidebar',values={'path':str(sibling)})
                self.assertTrue(sibling.exists())
            for action,values in [('script',{'path':''}),('unknown',{}),('email',[]),('clear_sidebar',{'path':'outside'})]:
                with self.assertRaises(ValueError): call('run_test',action=action,values=values)


if __name__ == '__main__':
    unittest.main()
