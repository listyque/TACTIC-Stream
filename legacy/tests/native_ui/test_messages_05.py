"""0.5 message semantics: production services, real Select, test persistence.
Not a full server/DB/permissions/trigger integration test; see Store docstring.
"""
import ast
import copy
import json
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from message_test_store import Store,Stub,Row,ROOT
from tactic.core.messaging import is_new,message_content,subscription_search,object_message_key,timestamp
from tactic.core.message_commands import ChatCmd
from tactic.core.notification_filters import NotificationLogScope
from tactic.ui_api.message_service import MessageService,page_number
from tactic.ui_api.contracts import ApiError,revision

class Backend(MessageService):
 site='';allow_writes=True
 def __init__(self,store):self.store=store;self.object=SimpleNamespace(get_base_search_type=lambda:'fixture/item',get_search_key=lambda:'fixture/item?project=test&code=ONE',get_sobject_dict=lambda:{'code':'ONE','name':'Test'})
 def _project(self):return self.store.project
 def _stub(self):return Stub(self.store)
 def _write(self,callback):
  if not self.allow_writes:raise ApiError(403,'read_only','Writes disabled')
  with self.store.db:return callback()
 def _object(self,*a):return self.object
 def open_target(self,target):
  if target=='record':return {'kind':'table','search_type':'fixture/item'}
  if target=='readonly':return {'kind':'message-center','handler':'tactic.ui.app.SubscriptionWdg','options':{}}
  if target=='chat':return {'kind':'message-center','handler':'tactic.ui.app.ChatSessionWdg','options':{'key':'pair'}}
  if target=='events':return {'kind':'message-center','handler':'tactic.ui.app.SubscriptionWdg','options':{'category':'sobject'}}
  raise ApiError(403,'target','Bad target')

class MessageTests(unittest.TestCase):
 def setUp(self):
  self.store=Store();self.store.seed();self.backend=Backend(self.store);self.binding=self.store.bind();self.binding.__enter__()
 def tearDown(self):self.binding.__exit__(None,None,None);self.store.close()
 def op(self,method,path,**data):return self.backend.message_operation(method,path,data)
 def history(self,code='pair',**kw):return self.op('GET','/message-history',message_code=code,**kw)
 def test_subscription_join_is_real_select_and_project_scoped(self):
  data=self.op('GET','/messages');keys={x['message_code'] for x in data['items']}
  self.assertEqual(keys,{'pair','group','legacy','event','progress','orphan'})
  self.assertTrue(any('LEFT OUTER JOIN' in s for s in self.store.statements))
 def test_category_filter(self):self.assertEqual({r['message_code'] for r in self.op('GET','/messages',category='chat')['items']},{'pair','group','legacy'})
 def test_new_filter_not_overwritten(self):
  item=self.store.get('subscription',message_code='pair',login='alice');item.set_value('last_cleared','2099-01-01');item.commit()
  keys={r['message_code'] for r in self.op('GET','/messages',mode='new')['items']};self.assertNotIn('pair',keys);self.assertNotIn('orphan',keys);self.assertIn('event',keys)
 def test_new_filter_does_not_leak_foreign_or_other_login(self):self.assertNotIn('foreign',{r['message_code'] for r in self.op('GET','/messages',mode='new')['items']})
 def test_pagination_total(self):
  a=self.op('GET','/messages',limit=2);b=self.op('GET','/messages',limit=2,offset=2)
  self.assertEqual(a['total'],6);self.assertTrue(a['has_more']);self.assertFalse(set(x['message_code'] for x in a['items'])&set(x['message_code'] for x in b['items']))
 def test_history_preserves_identical_text(self):
  rows=self.history()['items'];self.assertEqual(rows[-1]['content']['text'],rows[-2]['content']['text']);self.assertNotEqual(rows[-1]['id'],rows[-2]['id'])
 def test_history_keyset_pages_no_gaps(self):
  first=self.history(limit=20);second=self.history(limit=100,before=first['next_before']);self.assertEqual(len(first['items'])+len(second['items']),65)
  self.assertEqual(len({x['id'] for x in first['items']+second['items']}),65)
 def test_history_ascending(self):self.assertEqual([int(x['id']) for x in self.history()['items']],sorted(int(x['id']) for x in self.history()['items']))
 def test_welcome_not_fabricated_as_log(self):self.assertEqual(self.history('group')['items'],[]);self.assertEqual(self.history('group')['latest']['content']['text'],'Welcome!!!')
 def test_private_channel_denied_even_admin(self):
  with self.assertRaises(ApiError) as e:self.history('private')
  self.assertEqual(e.exception.status,403)
 def test_foreign_project_channel_denied(self):
  with self.assertRaises(ApiError):self.history('foreign')
 def test_projectless_history_preserved(self):
  self.store.log('legacy','From another project',project='other');self.assertTrue(self.history('legacy')['legacy_global']);self.assertEqual(len(self.history('legacy')['items']),1)
 def test_new_scoped_chat_filters_foreign_logs(self):
  self.store.row('message_log',message_code='pair',message='OTHER SECRET',project_code='other',category='chat')
  self.assertNotIn('OTHER SECRET',[x['content']['text'] for x in self.history()['items']])
 def test_duplicate_subscription_diagnostic(self):
  self.store.row('subscription',message_code='pair',login='alice',category='chat',project_code='test')
  with self.assertRaises(ApiError) as e:self.history()
  self.assertEqual(e.exception.code,'duplicate_subscription')
 def test_orphan_channel_explicit_empty(self):self.assertIsNone(self.history('orphan')['latest']);self.assertFalse(self.history('orphan')['can_ack'])
 def test_ack_uses_observed_timestamp(self):
  h=self.history();r=self.op('PATCH','/subscriptions',message_code='pair',revision=h['revision'],action='acknowledge')
  self.assertEqual(r['last_cleared'],h['latest']['timestamp']);self.assertFalse(r['read_receipt']);self.assertFalse(self.history()['new'])
 def test_ack_conflict_when_message_changes(self):
  h=self.history();self.store.log('pair','New event')
  with self.assertRaises(ApiError) as e:self.op('PATCH','/subscriptions',message_code='pair',revision=h['revision'],action='acknowledge')
  self.assertEqual(e.exception.status,409)
 def test_ack_same_timestamp_different_log_detected(self):
  h=self.history();self.store.row('message_log',message_code='pair',message='Same timestamp',timestamp=h['latest']['timestamp'],project_code='test')
  with self.assertRaises(ApiError):self.op('PATCH','/subscriptions',message_code='pair',revision=h['revision'],action='acknowledge')
 def test_ack_requires_action(self):
  with self.assertRaises(ApiError):self.op('PATCH','/subscriptions',message_code='pair',revision=self.history()['revision'],action='read')
 def test_unsubscribe_deletes_only_own_row(self):
  h=self.history();n=self.store.search('sthpw/message_log').get_count()
  r=self.op('DELETE','/subscriptions',message_code='pair',revision=h['revision'],confirm='UNSUBSCRIBE')
  self.assertFalse(r['deleted_messages']);self.assertIsNotNone(self.store.get('message',code='pair'));self.assertIsNotNone(self.store.get('subscription',message_code='pair',login='bob'));self.assertEqual(n,self.store.search('sthpw/message_log').get_count())
 def test_unsubscribe_confirmation_required(self):
  with self.assertRaises(ApiError):self.op('DELETE','/subscriptions',message_code='pair',revision=self.history()['revision'])
 def test_configured_subscription_default_disables_unsubscribe(self):
  h=self.history(target='readonly');self.assertFalse(h['can_unsubscribe'])
  with self.assertRaises(ApiError):self.op('DELETE','/subscriptions',target='readonly',message_code='pair',revision=h['revision'],confirm='UNSUBSCRIBE')
 def test_configured_chat_key_cannot_be_overridden(self):self.assertEqual(self.history('private',target='chat')['message_code'],'pair')
 def test_configured_event_category_is_not_chat(self):
  with self.assertRaises(ApiError):self.history(target='events')
 def test_send_uses_actual_log_message_sqlite_body(self):
  n=self.store.search('sthpw/message_log').get_count();self.op('POST','/message-send',message_code='pair',message='Привет <b>текст</b>',request_id='send-original-0001')
  self.assertEqual(self.store.search('sthpw/message_log').get_count(),n+1);h=self.history();self.assertEqual(h['items'][-1]['content']['text'],'Привет <b>текст</b>');self.assertEqual(h['items'][-1]['content']['kind'],'chat')
 def test_send_key_is_literal_not_expression(self):
  self.store.chat("chat'[]",['alice','bob']);self.op('POST','/message-send',message_code="chat'[]",message='Literal key',request_id='send-original-0002')
  self.assertEqual(self.history("chat'[]")['latest']['content']['text'],'Literal key')
 def test_send_retry_is_idempotent_in_single_process(self):
  d=dict(message_code='pair',message='One',request_id='send-original-0003');a=self.op('POST','/message-send',**d);n=self.store.search('sthpw/message_log').get_count();b=self.op('POST','/message-send',**d)
  self.assertEqual(a,b);self.assertEqual(n,self.store.search('sthpw/message_log').get_count())
 def test_retry_token_cannot_change_payload(self):
  self.op('POST','/message-send',message_code='pair',message='One',request_id='send-original-0004')
  with self.assertRaises(ApiError) as e:self.op('POST','/message-send',message_code='pair',message='Two',request_id='send-original-0004')
  self.assertEqual(e.exception.status,409)
 def test_cached_send_still_checks_membership(self):
  d=dict(message_code='pair',message='One',request_id='send-original-0005');self.op('POST','/message-send',**d);self.store.get('subscription',message_code='pair',login='alice').delete()
  with self.assertRaises(ApiError):self.op('POST','/message-send',**d)
 def test_cached_send_still_checks_new_widget_category(self):
  d=dict(message_code='pair',message='Same operation',request_id='send-category-0001')
  self.op('POST','/message-send',**d)
  with self.assertRaises(ApiError) as e:self.op('POST','/message-send',target='events',**d)
  self.assertEqual(e.exception.status,403)
 def test_cannot_send_over_system_event(self):
  with self.assertRaises(ApiError):self.op('POST','/message-send',message_code='event',message='overwrite',request_id='send-original-0006')
 def test_send_invalid_text_rejected(self):
  for v in ('','   ','x\x00y','x'*16001,{},None):
   with self.subTest(v=str(v)[:20]),self.assertRaises(ApiError):self.op('POST','/message-send',message_code='pair',message=v,request_id='send-original-0007')
 def test_read_only_preserved(self):
  self.backend.allow_writes=False;self.assertFalse(self.history()['can_send'])
  with self.assertRaises(ApiError):self.op('POST','/message-send',message_code='pair',message='No',request_id='send-original-0008')
 def test_sqlite_log_history_false(self):
  n=self.store.search('sthpw/message_log').get_count();Stub(self.store).log_message('pair','Latest only',category='chat',log_history=False)
  self.assertEqual(n,self.store.search('sthpw/message_log').get_count());self.assertEqual(self.history()['latest']['content']['text'],'Latest only')
 def test_sqlite_log_message_dict(self):
  Stub(self.store).log_message('event',{'search_type':'sthpw/note','update_data':{'note':'Тест'}},category='sobject')
  self.assertEqual(self.history('event')['latest']['content']['text'],'Комментарий: Тест')
 def test_chat_exact_participant_set(self):
  cmd=ChatCmd(users=['bob']);cmd.execute();self.assertEqual(cmd.info['message_code'],'pair');self.assertFalse(cmd.info['created'])
 def test_chat_group_not_confused_with_pair(self):
  cmd=ChatCmd(users=['carol','bob']);cmd.execute();self.assertEqual(cmd.info['message_code'],'group')
 def test_chat_new_participants_creates_scoped_rows(self):
  cmd=ChatCmd(users=['outsider','bob']);cmd.execute();self.assertTrue(cmd.info['created']);m=self.store.get('message',code=cmd.info['message_code']);self.assertEqual(m.get_value('project_code'),'test')
  rows=self.store.search('sthpw/subscription');rows.add_filter('message_code',m.get_code());self.assertEqual({x.get_value('login') for x in rows.get_sobjects()},{'alice','bob','outsider'})
 def test_chat_legacy_exact_group_reused(self):
  cmd=ChatCmd(users=['carol']);cmd.execute();self.assertEqual(cmd.info['message_code'],'legacy')
 def test_chat_invalid_user_rejected_before_writes(self):
  n=self.store.search('sthpw/message').get_count()
  for users in ([],None,'bob',['retired'],['no-such'],['alice'],['bad\x00login']):
   with self.subTest(users=users),self.assertRaises(Exception):ChatCmd(users=users).execute()
  self.assertEqual(n,self.store.search('sthpw/message').get_count())
 def test_create_chat_operation_retry(self):
  a=self.op('POST','/chats',users=['outsider'],request_id='create-chat-00001');b=self.op('POST','/chats',users=['outsider'],request_id='create-chat-00001');self.assertEqual(a,b)
 def test_picker_excludes_self_retired(self):
  names={x['login'] for x in self.op('GET','/chat-users')['items']};self.assertEqual(names,{'bob','carol','outsider'})
 def test_object_subscription_original_key(self):
  r=self.op('GET','/record-subscription',target='record',key='KEY');self.assertEqual(r['message_code'],'fixture/item?project=test&code=ONE')
 def test_object_subscription_actual_api_method(self):
  r=self.op('GET','/record-subscription',target='record',key='KEY');self.op('POST','/record-subscription',target='record',key='KEY',revision=r['revision']);s=self.store.get('subscription',message_code=r['message_code'],login='alice');self.assertEqual(s.get_value('category'),'sobject');self.assertEqual(s.get_value('project_code'),'test')
 def test_object_subscription_revision_changed(self):
  r=self.op('GET','/record-subscription',target='record',key='KEY');self.backend.object.get_sobject_dict=lambda:{'code':'ONE','name':'Changed'}
  with self.assertRaises(ApiError):self.op('POST','/record-subscription',target='record',key='KEY',revision=r['revision'])
 def test_orphan_subscription_can_be_removed_without_history(self):
  h=self.history('orphan');r=self.op('DELETE','/subscriptions',message_code='orphan',revision=h['revision'],confirm='UNSUBSCRIBE');self.assertTrue(r['unsubscribed'])
 def test_invalid_pagination(self):
  for data in ({'limit':0},{'limit':True},{'before':-1},{'before':'1 OR 1=1'},{'limit':101}):
   with self.subTest(data=data),self.assertRaises(ApiError):self.history(**data)
 def test_large_id_not_truncated_to_javascript_float(self):self.assertEqual(page_number('9223372036854775807','before',2**63-1),2**63-1)

class NotificationTests(unittest.TestCase):
 def setUp(self):
  self.store=Store();self.binding=self.store.bind();self.binding.__enter__()
  for id,p,owner in [(1,'test','alice'),(2,'test','bob'),(3,'other','alice'),(4,'test','alice')]:
   self.store.row('notification_log',project_code=p,subject='Email '+str(id),message='<script>untrusted</script>')
   self.store.row('notification_login',notification_log_id=id,project_code=p,login=owner,type='to')
 def tearDown(self):self.binding.__exit__(None,None,None);self.store.close()
 def test_original_notification_scope_current_recipient_and_project(self):
  q=self.store.search('sthpw/notification_log');NotificationLogScope().alter_search(q);self.assertEqual([x.get_id() for x in q.get_sobjects()],[1,4])
 def test_no_recipient_means_no_results(self):
  self.store.login='nobody';q=self.store.search('sthpw/notification_log');NotificationLogScope().alter_search(q);self.assertEqual(q.get_sobjects(),[])
 def test_duplicate_recipients_do_not_duplicate_logs(self):
  self.store.row('notification_login',notification_log_id=1,project_code='test',login='alice',type='cc');q=self.store.search('sthpw/notification_log');NotificationLogScope().alter_search(q);self.assertEqual(q.get_count(),2)
 def test_recipient_provider_batches_ids(self):
  b=Backend(self.store);r=b._notification_recipients([1,4]);self.assertEqual(r,{'1':'to: alice','4':'to: alice'})
 def test_notification_widget_cannot_override_hidden_recipient_scope(self):
  from tactic.core.config_model import target_spec
  source={'search_type':'sthpw/login','view':'unrestricted','native_notification_scope':False}
  result=target_spec('pyasm.prod.site.MyNotificationLogWdg',source)
  self.assertEqual(result['search_type'],'sthpw/notification_log')
  self.assertTrue(result['options']['native_notification_scope'])
  self.assertFalse(source['native_notification_scope'])
 def test_production_defaults_retain_hidden_scope_with_real_select(self):
  from tactic.ui_api.extended_backend import ExtendedBackend
  from tactic.ui_api.config_backend import ConfigBackend
  backend=object.__new__(ExtendedBackend);backend._project=lambda:self.store.project
  search=self.store.search('sthpw/notification_log')
  with patch.object(ConfigBackend,'_defaults'):
   backend._defaults(search,'sthpw/notification_log',{'native_notification_scope':True})
  self.assertEqual([r.get_id() for r in search.get_sobjects()],[1,4])
 def test_production_direct_object_check_reapplies_recipient_scope(self):
  from tactic.ui_api.extended_backend import ExtendedBackend
  from tactic.ui_api.config_backend import ConfigBackend
  backend=object.__new__(ExtendedBackend);backend._project=lambda:self.store.project
  backend.active_target={'options':{'native_notification_scope':True}}
  for ident,allowed in ((1,True),(2,False),(3,False),(4,True)):
   row=self.store.get('notification_log',id=ident)
   with self.subTest(id=ident),patch.object(ConfigBackend,'_object',return_value=row):
    if allowed:self.assertIs(backend._object('sthpw/notification_log',row.get_search_key()),row)
    else:
     with self.assertRaises(ApiError) as e:backend._object('sthpw/notification_log',row.get_search_key())
     self.assertEqual(e.exception.code,'notification_recipient')
 def test_batch_recipient_cache_is_restored_after_serialization_error(self):
  from tactic.ui_api.extended_backend import ExtendedBackend
  backend=object.__new__(ExtendedBackend);backend._project=lambda:self.store.project
  previous={'999':'previous-context'};backend._notification_recipient_cache=previous
  rows=[self.store.get('notification_log',id=1),self.store.get('notification_log',id=4)]
  with patch.object(backend,'_notification_recipients',wraps=backend._notification_recipients) as provider:
   with patch.object(backend,'_serialize',side_effect=ValueError('injected serialization failure')):
    with self.assertRaises(ValueError):backend._serialize_many(rows,{'fields':[{'provider':'notification-recipients'}]})
   provider.assert_called_once_with([1,4])
  self.assertIs(backend._notification_recipient_cache,previous)
 def test_recipient_batch_does_not_include_other_project_delivery_rows(self):
  self.store.row('notification_login',notification_log_id=1,project_code='other',login='hidden',type='bcc')
  self.assertEqual(Backend(self.store)._notification_recipients([1]),{'1':'to: alice'})
 def test_hidden_filter_source_algorithm_retained(self):
  import hashlib
  info=json.loads((ROOT/'tests/native_ui/source-provenance-05.json').read_text())['methods'][0]
  cls=next(n for n in ast.parse((ROOT/info['target']).read_text()).body if isinstance(n,ast.ClassDef))
  actual=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==info['method'])
  self.assertEqual(hashlib.sha256(ast.dump(actual,include_attributes=False).encode()).hexdigest(),info['ast_sha256'])

class MessageProjectionTests(unittest.TestCase):
 def test_plain_text_not_html(self):self.assertEqual(message_content('<img onerror=alert(1)>','chat')['text'],'<img onerror=alert(1)>')
 def test_dict_not_evaluated(self):self.assertIn('__import__',message_content("{'message':__import__('os')}")['text'])
 def test_invalid_progress_no_nan(self):self.assertIsNone(message_content({'progress':float('nan')},'progress')['progress'])
 def test_progress_clamps(self):self.assertEqual(message_content({'progress':200},'progress')['progress'],100)
 def test_sobject_changes_preserve_false_and_zero(self):self.assertEqual(message_content({'update_data':{'n':0,'x':False}},'sobject')['changes'],[{'field':'n','value':0},{'field':'x','value':False}])
 def test_timestamp_unknown_not_new(self):self.assertFalse(is_new('invalid',None))
 def test_new_timestamp_equal_cleared_is_not_new(self):self.assertFalse(is_new('2026-01-01','2026-01-01'))
 def test_timezone_aware_comparison(self):self.assertFalse(is_new('2026-01-01T12:00:00+02:00','2026-01-01T10:00:00Z'))
 def test_original_task_parent_message_key(self):
  obj=SimpleNamespace(get_base_search_type=lambda:'sthpw/task',get_value=lambda n,**kw:{'search_type':'fixture/item?project=test','search_code':'ONE'}.get(n))
  self.assertEqual(object_message_key(obj),'fixture/item?project=test&code=ONE')
 def test_unsupported_system_subscription_not_invented(self):
  with self.assertRaises(ValueError):object_message_key(SimpleNamespace(get_base_search_type=lambda:'sthpw/login'))

if __name__=='__main__':unittest.main()
