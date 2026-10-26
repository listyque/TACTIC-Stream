"""Account-owned provider profiles with encrypted, write-only credentials."""
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
from uuid import uuid4

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.config import config_file_lock
from pyasm.search import Search
from pyasm.security.security import _require_admin
from .agent_request_cmd import AgentRequestCmd, HOST_TTL, identity, text

KINDS = {
    'codex': ('Codex account', ''),
    'openai': ('OpenAI', 'https://api.openai.com/v1'),
    'compatible': ('OpenAI-compatible API', ''),
    'local': ('Local model server', 'http://127.0.0.1:11434/v1'),
    'anthropic': ('Anthropic', 'https://api.anthropic.com/v1'),
    'gemini': ('Gemini', 'https://generativelanguage.googleapis.com/v1beta'),
}


def profile_path():
    owner = hashlib.sha256(Environment.get_user_name().encode()).hexdigest()
    return Path(Environment.get_data_dir()) / 'agent_providers' / (owner + '.json')


def read_profiles(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else dict(default='codex', profiles=[
        dict(id='codex', name='Codex', kind='codex', url='', credential='', secret_env='', enabled=True,
             default_model='', models=[], status='unchecked', error='', check='')])


def revision(document):
    return hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()


def public(document):
    profiles = [dict({key: value for key, value in row.items() if key != 'credential'}, has_secret=bool(row.get('credential'))) for row in document['profiles']]
    return dict(default=document['default'], profiles=profiles, revision=revision(document),
                kinds=[dict(value=key, label=label, url=url) for key, (label, url) in KINDS.items()])


def captured_target(code):
    document = read_profiles(profile_path())
    profile = next((row for row in document['profiles'] if row['id']==code and row['enabled']), None)
    if profile is None:
        raise ValueError('Choose an enabled provider connection')
    return {key: profile[key] for key in ('id','kind','url')}


def write_profiles(path, document):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as output:
        os.chmod(temporary, 0o600)
        json.dump(document, output, ensure_ascii=False, indent=2)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


class AgentProviderCmd(Command):
    def execute(self):
        _require_admin()
        if self.kwargs.get('project_code') != Project.get_project_code():
            raise ValueError('Provider project mismatch')
        path = profile_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        action = self.kwargs.get('action')
        if action not in ('state', 'save', 'remove', 'check', 'host_profiles', 'report'):
            raise ValueError('Unknown provider action')
        with config_file_lock(path.with_suffix('.lock')):
            document = read_profiles(path)
            if action == 'state':
                self.info = public(document)
                return
            if action in ('host_profiles', 'report'):
                request = AgentRequestCmd()
                request.sql = Search('config/trigger').get_sql()
                request.owner = Environment.get_user_name()
                host = request.load('spt_agent_host', identity(self.kwargs.get('host_id')))
                if time.time() - host['seen'] > HOST_TTL:
                    raise ValueError('External host is offline')
                if action == 'host_profiles':
                    from tactic_stream.provider_credentials import host_envelope, unseal
                    self.info = public(document)
                    for profile in self.info['profiles']:
                        original = next(row for row in document['profiles'] if row['id'] == profile['id'])
                        if original.get('credential') and profile['enabled']:
                            scope = Environment.get_user_name() + ':' + host['host_id'] + ':' + profile['id']
                            profile['credential_scope'] = scope
                            try:
                                profile['credential_envelope'] = host_envelope(unseal(original['credential']), host['capabilities'].get('credential_key'), scope)
                            except (ValueError, OSError):
                                profile['credential_error'] = 'The provider key could not be opened for this host; re-enter it or reconnect the host'
                    return
                profile = next((row for row in document['profiles'] if row['id'] == self.kwargs.get('provider')), None)
                if profile is None or self.kwargs.get('check') != profile.get('check'):
                    self.info = public(document)
                    return
                models = self.kwargs.get('models')
                if not isinstance(models, list) or len(models) > 1000 or any(
                        not isinstance(model, dict) or set(model) - {'id', 'label', 'efforts', 'is_default', 'modalities'}
                        or not isinstance(model.get('id'), str) or not model['id'] or len(model['id']) > 256
                        or not isinstance(model.get('label'), str) or len(model['label']) > 256
                        or not isinstance(model.get('efforts', []), list) or len(model.get('efforts', [])) > 20
                        or type(model.get('is_default', False)) is not bool
                        or not isinstance(model.get('modalities', []), list)
                        or any(value not in ('text', 'image') for value in model.get('modalities', []))
                        or any(not isinstance(value, str) or len(value) > 32 for value in model.get('efforts', [])) for model in models):
                    raise ValueError('Invalid provider model catalogue')
                error = text(self.kwargs.get('error', ''), 2000, empty=True)
                if profile.get('credential'):
                    from tactic_stream.provider_credentials import unseal
                    try:
                        error = error.replace(unseal(profile['credential']), '[redacted]')
                    except (ValueError, OSError):
                        error = 'The provider key cannot be opened by this server vault; re-enter it in AI providers'
                profile.update(models=models, error=error, status='failed' if error else 'connected', checked=int(time.time()))
            else:
                if self.kwargs.get('expected_revision') != revision(document):
                    raise ValueError('Provider settings changed. Reload before saving.')
                code = self.kwargs.get('provider', '')
                profile = next((row for row in document['profiles'] if row['id'] == code), None)
                if action == 'save':
                    values = self.kwargs.get('document')
                    fields = {'name', 'kind', 'url', 'secret', 'secret_env', 'clear_secret', 'enabled', 'default_model', 'default'}
                    if not isinstance(values, dict) or set(values) != fields:
                        raise ValueError('Invalid provider settings')
                    if values['kind'] not in KINDS or any(type(values[key]) is not bool for key in ('enabled', 'clear_secret', 'default')):
                        raise ValueError('Choose a provider type and valid switches')
                    if code and profile is None:
                        raise ValueError('Provider profile is unavailable')
                    if (code == 'codex') != (values['kind'] == 'codex'):
                        raise ValueError('Use the existing Codex account profile')
                    url = text(values['url'], 2048, empty=values['kind'] == 'codex').rstrip('/')
                    if values['kind'] != 'codex':
                        parsed = urlsplit(url)
                        if (parsed.scheme not in (('http', 'https') if values['kind'] == 'local' else ('https',))
                                or not parsed.hostname or parsed.username is not None or parsed.password is not None
                                or parsed.query or parsed.fragment or any(char.isspace() for char in url)):
                            raise ValueError('Use an HTTPS API base URL without credentials, query or fragment; local profiles also support HTTP')
                    if profile is None:
                        if len(document['profiles']) >= 20:
                            raise ValueError('Use at most 20 provider profiles')
                        profile = dict(id=str(uuid4()), credential='')
                        document['profiles'].append(profile)
                    secret = text(values['secret'], 4096, empty=True)
                    secret_env = text(values['secret_env'], 128, empty=True)
                    if secret_env and (not secret_env.replace('_', '').isalnum() or secret_env[0].isdigit()):
                        raise ValueError('Use an environment variable name, not a credential value')
                    if secret and secret_env:
                        raise ValueError('Choose an API key or a host environment variable')
                    if values['clear_secret'] or values['kind'] == 'codex' or secret_env:
                        profile['credential'] = ''
                    elif secret:
                        from tactic_stream.provider_credentials import seal
                        profile['credential'] = seal(secret)
                    profile.update(name=text(values['name'], 128), kind=values['kind'], url=url, secret_env=secret_env,
                        enabled=values['enabled'], default_model=text(values['default_model'], 256, empty=True),
                        models=[], status='unchecked', error='', check=str(uuid4()))
                    if values['default']:
                        document['default'] = profile['id']
                elif profile is None:
                    raise ValueError('Provider profile is unavailable')
                elif action == 'remove':
                    if code == 'codex':
                        raise ValueError('Disable the Codex account profile instead of removing it')
                    document['profiles'].remove(profile)
                    if document['default'] == code:
                        document['default'] = 'codex'
                else:
                    profile.update(check=str(uuid4()), status='waiting', error='')
            write_profiles(path, document)
            self.info = public(document)
