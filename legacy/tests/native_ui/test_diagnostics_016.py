"""New logging/dispatch regressions. No user installation or fake security bypass."""
import contextvars
import concurrent.futures
import hashlib
import json
import logging
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from tactic.ui_api import action_log as log
from tactic.ui_api.api import Request,Api
from tactic.ui_api.contracts import ApiError
from tactic.core.config_model import target_spec,ConfigSource,ConfigModel,SidebarProjection
from tactic.ui_api.global_admin_service import AUDITED_BUTTONS


class DiagnosticTests(unittest.TestCase):
    def trace(self,request=None):return log.RequestTrace(request or Request('POST','/query',headers={}), 'server-request-1').begin()

    def test_no_values_or_secrets_from_body(self):
        values={'password':'PASSWORD-SHOULD-NOT-APPEAR','description':'CONFIDENTIAL CONTENT',
                'token':'TOKEN-PRIVATE','price':'123-secret-price'}
        with patch.object(log,'emit') as output:
            t=self.trace();t.parameters({'project':'admin','values':values,'password':'login-secret','config_xml':'<private/>'})
            t.finish(200,{'ticket':'DONTLOG','csrf':'PRIVATE','user':values})
        record=output.call_args.args[0];content=json.dumps(record)
        for secret in ['PASSWORD-SHOULD','CONFIDENTIAL','TOKEN-PRIVATE','123-secret-price','login-secret','<private/>','DONTLOG','PRIVATE']:
            self.assertNotIn(secret,content)
        self.assertEqual(record['fields'],['description','price'])

    def test_filter_operands_not_logged(self):
        shape=log.query_shape({'where':{'op':'and','children':[{'field':'status','op':'eq','value':'classified-status'},{'field':'password','op':'eq','value':'secret'}]}})
        self.assertIn('status:eq(?)',shape);self.assertNotIn('classified-status',shape);self.assertNotIn('password',shape)

    def test_range_limit_sort_in_request(self):
        with patch.object(log,'emit') as output:
            t=self.trace();t.parameters({'project':'test','limit':50,'offset':100,'sort':{'field':'code','direction':'desc'}});t.finish(200,{'items':[{},{}],'total':400})
        record=output.call_args.args[0];self.assertEqual((record['rows'],record['total'],record['limit'],record['offset']),(2,400,50,100));self.assertEqual(record['sort'],['code:desc'])

    def test_metadata_authoritative_renderer_in_log(self):
        with patch.object(log,'emit') as output:
            t=self.trace();t.parameters({'project':'test','target':'a/~cell/b'})
            t.resolve({'id':'a','handler':'TableLayoutWdg','kind':'table'})
            t.resolve({'id':'a/~cell/b','handler':'PipelineToolWdg','kind':'pipeline'});t.finish(200,{})
        record=output.call_args.args[0];self.assertEqual(record['handler'],'PipelineToolWdg');self.assertEqual(record['renderer'],'pipeline')

    def test_request_context_reset(self):
        with patch.object(log,'emit'):
            t=self.trace();t.finish(400,{},'validation')
        self.assertIsNone(log.TRACE.get())

    def test_error_does_not_dump_exception_message(self):
        with patch.object(log,'emit') as output:
            t=self.trace();t.finish(500,{'error':{'message':'password=SHOULDNOT'}},'RuntimeError')
        record=output.call_args.args[0];self.assertEqual(record['error'],'RuntimeError');self.assertNotIn('SHOULDNOT',json.dumps(record))

    def test_health_and_preferences_quiet_by_default(self):
        with patch.object(log,'emit') as output,patch.object(log,'MODE','actions'):
            for route in ['/health','/ui-state','/upload-status']:
                self.trace(Request('GET',route)).finish(200,{})
        self.assertFalse(output.called)

    def test_successful_preference_write_is_logged(self):
        with patch.object(log,'emit') as output,patch.object(log,'MODE','actions'):
            self.trace(Request('PATCH','/ui-state')).finish(200,{})
        self.assertTrue(output.called)

    def test_empty_filters_are_not_noise(self):
        self.assertEqual(log.query_shape({'where':{'op':'and','children':[]}}),'')

    def test_added_module_aliases_match_actual_source_classes(self):
        for name,module in [('ProjectCreateWdg','tactic/ui/app/page_header_wdg.py'),('UserConfigWdg','tactic/ui/startup/project_config_wdg.py')]:
            self.assertIn('class '+name+'(', (ROOT/'src'/module).read_text())
            self.assertNotEqual(target_spec(module[:-3].replace('/','.')+'.'+name,{})['kind'],'unsupported')

    def test_verbose_and_errors_not_quiet(self):
        with patch.object(log,'emit') as output,patch.object(log,'MODE','verbose'):
            self.trace(Request('GET','/ui-state')).finish(200,{})
        self.assertTrue(output.called)
        with patch.object(log,'emit') as output,patch.object(log,'MODE','actions'):
            self.trace(Request('GET','/ui-state')).finish(409,{},'conflict')
        self.assertTrue(output.called)

    def test_off_mode(self):
        with patch.object(log,'emit') as output,patch.object(log,'MODE','off'):
            self.trace().finish(200,{})
        self.assertFalse(output.called)

    def test_correlation_header_is_bounded(self):
        for value,allowed in [('ui_123',True),('x'*65,False),('bad\nLOG FORGED',False)]:
            t=log.RequestTrace(Request('GET','/open',headers={'x-tactic-action-id':value}),'abc')
            self.assertEqual('action_id' in t.event,allowed)

    def test_log_controls_and_console_escape_are_not_executed(self):
        line=log.human({'source':'server','time':'\n','user':'\x1b[31mUSER\nforge','route':'/query','target':'\rnext'})
        self.assertNotIn('\x1b',line);self.assertNotIn('\n',line);self.assertNotIn('\r',line)

    def test_no_native_import_required_for_legacy(self):
        source=(ROOT/'src/pyasm/command/command.py').read_text()
        self.assertIn("sys.modules.get('tactic.ui_api.action_log')",source)
        self.assertNotIn('import action_log',source)

    def test_concurrent_requests_do_not_exchange_identity(self):
        results=[]
        def task(index):
            t=self.trace();t.identity(SimpleNamespace(login=str(index),site=''));log.command_started(SimpleNamespace())
            result=t.event['user'];t.finish(200,{})
            return result
        with patch.object(log,'MODE','off'), concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(task,range(30)))
        self.assertEqual(results,[str(i) for i in range(30)])

    def test_native_access_filter_does_not_hide_legacy_or_errors(self):
        f=log.NativeAccessFilter()
        make=lambda text:logging.LogRecord('cherrypy.access',20,'',0,text,(),None)
        with patch.object(log,'MODE','actions'):
            self.assertFalse(f.filter(make('"GET /api/ui/v2/query HTTP/1.1" 200 123')))
            self.assertTrue(f.filter(make('"GET /tactic/admin/ HTTP/1.1"')))
            self.assertTrue(f.filter(make('DB error')))
            self.assertTrue(f.filter(make('"POST /api/ui/v2/upload HTTP/1.1" 413 0')))
            self.assertTrue(f.filter(make('"GET /api/ui/v2/query HTTP/1.1"')))
        with patch.object(log,'MODE','off'):
            self.assertTrue(f.filter(make('"GET /api/ui/v2/query HTTP/1.1" 200 123')))

    def test_client_event_is_not_server_confirmation(self):
        with patch.object(log,'emit') as output:
            result=log.client_events({'project':'p','events':[{'event':'cell.stage','action_id':'ui_1','field':'name','count':2}]},SimpleNamespace(login='real-user',site=''))
        event=output.call_args.args[0];self.assertEqual(result['accepted'],1);self.assertEqual(event['source'],'client');self.assertNotIn('status',event);self.assertEqual(event['user'],'real-user')

    def test_client_cannot_forge_user_or_server_event(self):
        for item in [{'event':'cell.stage','user':'admin'},{'event':'Command.finished'},{'event':'cell.stage','value':'secret'}]:
            with self.subTest(item=item), self.assertRaises(ApiError):
                log.client_events({'events':[item]},SimpleNamespace(login='a',site=''))

    def test_invalid_batch_has_no_partial_output(self):
        with patch.object(log,'emit') as output, self.assertRaises(ApiError):
            log.client_events({'events':[{'event':'cell.stage'},{'event':'random'}]},SimpleNamespace(login='a',site=''))
        self.assertFalse(output.called)

    def test_client_batch_limit(self):
        for events in [[],[{'event':'cell.stage'}]*33,'invalid']:
            with self.subTest(events=type(events)),self.assertRaises(ApiError):log.client_events({'events':events},SimpleNamespace(login='a',site=''))

    def test_client_event_route_needs_authentication(self):
        class Backend:
            mode='test'
        response=Api(Backend()).handle(Request('POST','/client-events',headers={'X-Tactic-UI':'1','Content-Type':'application/json'},body=b'{"events":[]}'))
        self.assertEqual(response.status,401)

    def test_tailer_outputs_only_structured_records_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'actions-1.jsonl';events=[];tail=log.ActionLogTailer(tmp,['1'],events.append)
            record={'source':'server','route':'/open','worker':'1','pid':100,'handler':'PipelineToolWdg','renderer':'pipeline'}
            path.write_text('PASSWORD RAW legacy output\n'+json.dumps(record)+'\n')
            tail.poll();tail.poll();self.assertEqual(len(events),1);self.assertIn('PipelineToolWdg',events[0]);self.assertNotIn('PASSWORD',events[0])

    def test_tailer_reassembles_partial_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'actions-1.jsonl';events=[];tail=log.ActionLogTailer(tmp,['1'],events.append)
            raw=json.dumps({'source':'client','event':'view.open','worker':'1'})+'\n'
            path.write_text(raw[:15]);tail.poll();self.assertEqual(events,[])
            with path.open('a') as f:f.write(raw[15:])
            tail.poll();self.assertEqual(len(events),1)

    def test_tailer_handles_file_rotation_and_new_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'actions-1.jsonl';events=[];tail=log.ActionLogTailer(tmp,['1'],events.append)
            for i in range(3):
                if path.exists():path.rename(Path(tmp)/('archive'+str(i)))
                path.write_text(json.dumps({'source':'client','event':'view.open','pid':i,'worker':'1'})+'\n');tail.poll()
            self.assertEqual(len(events),3)


class WidgetDispatchTests(unittest.TestCase):
    def test_short_module_and_export_pipeline_names(self):
        for name in ['PipelineToolWdg','tactic.ui.tools.PipelineToolWdg','tactic.ui.tools.pipeline_wdg.PipelineToolWdg','PipelineEditorWdg']:
            with self.subTest(name=name):self.assertEqual(target_spec('LinkWdg',{'class_name':name,'search_type':'sthpw/pipeline'})['kind'],'pipeline')

    def test_schema_whitespace_identifier(self):
        target=target_spec('LinkWdg',{'class_name':'\n tactic.ui.tools.schema_wdg.SchemaToolWdg \n'})
        self.assertEqual(target['kind'],'schema')

    def test_unknown_custom_class_not_guessed_by_name(self):
        target=target_spec('LinkWdg',{'class_name':'plugin.team.PipelineToolWdg','search_type':'sthpw/pipeline'})
        self.assertEqual(target['kind'],'unsupported');self.assertEqual(target['handler'],'plugin.team.PipelineToolWdg')

    def test_raw_pipeline_table_remains_table(self):
        target=target_spec('LinkWdg',{'search_type':'sthpw/pipeline','view':'manage'})
        self.assertEqual(target['kind'],'table')

    def test_raw_schema_table_remains_table(self):
        target=target_spec('LinkWdg',{'search_type':'sthpw/schema','view':'manage'})
        self.assertEqual(target['kind'],'table')

    def test_original_button_callbacks_audited_exactly(self):
        for stype,field in [('pipeline','editor'),('schema','create')]:
            root=ET.parse(ROOT/f'src/config2/search_type/widget/sthpw/{stype}-conf.xml').getroot()
            text=root.find(f"definition/element[@name='{field}']/display/cbjs_action").text
            digest=hashlib.sha256(' '.join(text.split()).encode()).hexdigest()
            self.assertEqual(AUDITED_BUTTONS[('sthpw/'+stype,field)][1],digest)
            self.assertNotEqual(AUDITED_BUTTONS[('sthpw/'+stype,field)][1],hashlib.sha256((text+'bad()').encode()).hexdigest())

    def test_scalar_option_whitespace_not_changed(self):
        target=target_spec('PipelineToolWdg',{'description':'  preserve whitespace\n'})
        self.assertEqual(target['options']['description'],'  preserve whitespace\n')

    def test_renderer_not_inferred_from_saved_workspace(self):
        source=(ROOT/'frontend/src/App.vue').read_text()
        self.assertIn("api.request('/open',{project,target:node.id})",source)
        self.assertNotIn('workspace.value.kind',source)

if __name__=='__main__':unittest.main()
