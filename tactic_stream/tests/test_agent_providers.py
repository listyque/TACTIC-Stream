"""Profile edits, encrypted storage/export, source revisions and owner scoping."""
import json
import unittest
from uuid import uuid4

from tests import test_agent_requests as fixture
try:
    from tactic_stream import provider_credentials as vault
except ImportError:
    vault = None

COMMAND = 'tactic.ui.panel.agent_provider_cmd.AgentProviderCmd'


@unittest.skipIf(vault is None, 'Install tactic-stream[agent] for provider tests')
class Profiles(unittest.TestCase):
    setUp = fixture.AgentRequests.setUp
    call = fixture.AgentRequests.call

    def provider(self, action, **values):
        return self.api.dispatch('execute_cmd', (self.auth, COMMAND, dict(action=action, project_code='one', **values)))['info']

    def test_write_only_keys_revision_and_bound_host_export(self):
        state = self.provider('state')
        self.assertEqual(state['default'], 'codex')
        values = dict(name='Claude fixture', kind='anthropic', url='https://api.anthropic.com/v1', secret='private-provider-fixture', secret_env='',
            clear_secret=False, enabled=True, default_model='', default=False)
        saved = self.provider('save', expected_revision=state['revision'], provider='', document=values)
        profile = next(row for row in saved['profiles'] if row['kind']=='anthropic')
        self.assertTrue(profile['has_secret'])
        self.assertNotIn('private-provider-fixture', json.dumps(saved))
        self.assertNotIn('credential', profile)
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.provider('save', expected_revision=state['revision'], provider=profile['id'], document=values)
        private, public = vault.new_host_key()
        self.call('heartbeat', host_id=self.host, label='Fixture', capabilities=dict(changes=True, trials=False, credential_key=public))
        encrypted = self.provider('host_profiles', host_id=self.host)
        self.assertNotIn('private-provider-fixture', json.dumps(encrypted))
        exported = next(row for row in encrypted['profiles'] if row['id']==profile['id'])
        self.assertEqual(vault.host_secret(exported['credential_envelope'], private, exported['credential_scope']), values['secret'])
        from tactic.ui.panel.agent_provider_cmd import read_profiles, profile_path
        from pyasm.search.search import RequestContext, request_context
        with request_context(RequestContext(self.store,'admin','one')):
            self.api.auth.bind_security('admin', self.auth['ticket'])
            stored = read_profiles(profile_path())
            self.assertNotIn('private-provider-fixture', json.dumps(stored))
        with self.assertRaises(ValueError):
            self.provider('host_profiles', host_id=str(uuid4()))
        reported = self.provider('report', host_id=self.host, provider=profile['id'], check=profile['check'],
            models=[], error='Failed with private-provider-fixture')
        self.assertNotIn('private-provider-fixture', json.dumps(reported))
        self.assertIn('[redacted]', next(row for row in reported['profiles'] if row['id']==profile['id'])['error'])
        cleared = self.provider('save', expected_revision=reported['revision'], provider=profile['id'], document=dict(values, secret='', clear_secret=True))
        self.assertFalse(next(row for row in cleared['profiles'] if row['id']==profile['id'])['has_secret'])

    def test_local_endpoints_and_remote_credential_url_refusal(self):
        state = self.provider('state')
        values = dict(name='Local fixture', kind='local', url='http://127.0.0.1:11434/v1', secret='', secret_env='',
            clear_secret=False, enabled=True, default_model='fixture', default=True)
        saved = self.provider('save', expected_revision=state['revision'], provider='', document=values)
        profile = next(row for row in saved['profiles'] if row['kind']=='local')
        self.assertEqual(saved['default'], profile['id'])
        for url in ('https://user:secret@api.example/v1', 'https://api.example/v1?key=hidden', 'http://api.example/v1'):
            with self.assertRaisesRegex(ValueError, 'API base URL'):
                self.provider('save', expected_revision=saved['revision'], provider=profile['id'], document=dict(values,kind='compatible',url=url))
        removed = self.provider('remove', expected_revision=saved['revision'], provider=profile['id'])
        self.assertEqual(removed['default'],'codex')

    def test_turn_captures_chosen_destination_and_old_clients_stay_codex(self):
        state = self.provider('state')
        values = dict(name='Local fixture', kind='local', url='http://127.0.0.1:11434/v1', secret='', secret_env='',
            clear_secret=False, enabled=True, default_model='fixture', default=True)
        state = self.provider('save', expected_revision=state['revision'], provider='', document=values)
        profile = next(row for row in state['profiles'] if row['kind']=='local')
        capabilities = dict(changes=True, trials=False, providers=[dict(id='codex',name='Codex',kind='codex'),
            {key:profile[key] for key in ('id','name','kind')}], models=[dict(id='fixture',label='Local fixture',provider=profile['id'],is_default=True)])
        self.call('heartbeat',host_id=self.host,label='Fixture',capabilities=capabilities)
        self.document.update(provider=profile['id'],model='fixture')
        row,_ = fixture.AgentRequests.submit(self)
        expected = {key:profile[key] for key in ('id','kind','url')}
        self.assertEqual(row['provider_target'],expected)
        changed = self.provider('save',expected_revision=state['revision'],provider=profile['id'],document=dict(values,url='http://127.0.0.1:11435/v1'))
        self.assertEqual(self.call('claim',host_id=self.host)['request']['provider_target'],expected)
        self.call('update',host_id=self.host,request_id=row['request_id'],status='completed')
        self.call('heartbeat',host_id=self.host,label='Fixture',capabilities=capabilities)
        resumed = self.call('message',request_id=row['request_id'],message_id=str(uuid4()),text='Continue')
        self.assertEqual(resumed['provider_target']['url'],'http://127.0.0.1:11435/v1')
        self.document.pop('provider');self.document.pop('model')
        capabilities['models'].append(dict(id='account-model',label='Account model',provider='codex',is_default=True))
        self.call('heartbeat',host_id=self.host,label='Fixture',capabilities=capabilities)
        old,_ = fixture.AgentRequests.submit(self)
        self.assertEqual(old['provider'],'codex')
        self.assertEqual(old['provider_target'],dict(id='codex',kind='codex',url=''))
        stale = self.provider('report',host_id=self.host,provider=profile['id'],check=profile['check'],models=[],error='Obsolete probe')
        self.assertEqual(stale['revision'],changed['revision'])
