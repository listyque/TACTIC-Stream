# Copyright (c) 2010, Southpaw Technology. See LICENSE.TACTIC.
"""SystemInfoWdg facts and original diagnostic actions, without the HTML shell."""
import getpass
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from pyasm.common import Config, Container, Environment
from pyasm.common.errors import SecurityException
from pyasm.command import Command


def require_admin():
    security = Environment.get_security()
    if security is None or not security.is_admin():
        raise SecurityException('System Info requires administrator access')


class SystemInfoWdg:
    @staticmethod
    def get_info() -> dict:
        require_admin()
        from tactic_stream import __version__
        from pyasm.biz import Project

        system = platform.uname()
        try:
            login = getpass.getuser()
        except OSError:
            login = ''
        sections = [dict(title='Server', fields=[
            ['TACTIC Stream', __version__],
            ['OS', system.system], ['Node Name', system.node],
            ['Release', system.release], ['Version', system.version],
            ['Machine', system.machine], ['CPU Count', str(os.cpu_count() or '—')],
            ['Login', login],
            ['Server time (UTC)', datetime.now(timezone.utc).isoformat()]],
        ), dict(title='Python', fields=[['Version', sys.version]])]
        environment = Container.get('Api:environ') or {}
        client = [['TACTIC User', Environment.get_user_name() or '']]
        client.append(['Project', Project.get_project_code()])
        if environment.get('HTTP_USER_AGENT'):
            client.append(['User Agent', environment['HTTP_USER_AGENT']])
        sections.append(dict(title='Client', fields=client))
        sections.append(dict(title='Mail Server', fields=[
            ['Server', Config.get_value('services', 'mailserver') or None],
        ]))
        roots = dict(Environment.get_asset_dirs())
        roots.setdefault('default', Environment.get_asset_dir())
        fields = []
        for alias, path in roots.items():
            fields.append([f'asset_base_dir ({alias})', path or None])
            if path:
                fields.append(['Writable (access check)', os.access(path, os.W_OK)])
        handoff = Environment.get_server_handoff_dir(include_ticket=False)
        fields.append(['Server handoff directory', handoff or None])
        if handoff:
            fields.append(['Writable (access check)', os.access(handoff, os.W_OK)])
        sections.append(dict(title='Asset Folders', fields=fields))
        from pyasm.security import Login
        account = Login.get_by_login('admin')
        email = account.get_value('email', no_exception=True) if account else ''
        directories = {}
        for client_os in ('win32', 'linux'):
            directories[client_os] = {
                key: Config.get_value('checkin', client_os + '_' + key) or ''
                for key in ('client_repo_dir', 'client_handoff_dir')}
            directories[client_os]['client_repo_dir'] = directories[client_os]['client_repo_dir'] or Environment.get_asset_dirs()
            directories[client_os]['client_handoff_dir'] = directories[client_os]['client_handoff_dir'] or str(Path(Environment.get_tmp_dir()) / 'handoff')
            for key, value in directories[client_os].items():
                fields.append([client_os + '_' + key, value])
        return dict(sections=sections, cpuCount=os.cpu_count() or 1, mailFrom=email or '',
                    mailConfigured=bool(Config.get_value('services', 'mailserver')),
                    directories=directories, project=Project.get_project_code(),
                    links=SystemInfoWdg.get_links(False), internalLinks=SystemInfoWdg.get_links(True))

    @staticmethod
    def connection_probe():
        require_admin()
        environment = Container.get('Api:environ') or {}
        return dict(port=environment.get('SERVER_PORT'), pid=os.getpid(), node=platform.node())

    @staticmethod
    def performance_probe():
        require_admin()
        from tactic_stream.server.interface import read_interface
        from pyasm.search import Search
        definition = read_interface('sthpw/login', 'table')
        search = Search('sthpw/login')
        search.set_limit(20)
        return dict(columns=len(definition.get('columns', [])), rows=len(search.get_sobjects()))

    @staticmethod
    def get_links(include_internal=False):
        require_admin()
        if type(include_internal) is not bool:
            raise ValueError('Choose whether to include built-in pages')
        from pyasm.biz import Project
        from pyasm.search import Search
        from tactic.core.sidebar_config import SidebarConfig
        names = []
        if include_internal:
            configs = []
            SidebarConfig.add_internal_config(configs, ['definition'])
            for config in configs:
                names.extend(config.get_element_names())
        search = Search('config/widget_config')
        search.add_filter('search_type', 'SideBarWdg')
        search.add_filter('view', 'definition')
        search.add_filter('login', None)
        for config in search.get_sobjects():
            names.extend(config.get_element_names())
        config = SidebarConfig.get_config('SideBarWdg', 'definition')
        project = Project.get_project_code()
        return [dict(name=name, title=config.get_element_title(name) or name,
                     url='/projects/' + quote(project, safe='') + '/?system_link=' + quote(name, safe=''))
                for name in dict.fromkeys(names) if 'separator' not in name.lower()]

    @staticmethod
    def resolve_link(name):
        require_admin()
        if not isinstance(name, str) or not name or len(name) > 256:
            raise ValueError('Choose a configured project page')
        from tactic.core.sidebar_config import SidebarConfig
        from pyasm.common.errors import UnsupportedContract
        config = SidebarConfig.get_config('SideBarWdg', 'definition')
        if name not in config.get_element_names():
            raise LookupError('Project page is not configured: ' + name)
        options = config.get_display_options(name)
        handler = config.get_display_handler(name).split('.')[-1]
        windows = {'SystemInfoWdg': 'system_info', 'ScriptEditorWdg': 'script_editor'}
        if handler in windows:
            return dict(window=windows[handler])
        if handler != 'LinkWdg' or not options.get('search_type'):
            raise UnsupportedContract('Project page handler is unavailable: ' + handler)
        return dict(search_type=options['search_type'], view=options.get('view') or 'table',
                    title=config.get_element_title(name) or name,
                    layoutView=options.get('view') if options.get('widget_key') == 'custom_layout' else '',
                    display=dict(handler='LinkWdg', options=options))

    @staticmethod
    def run_test(action, values=None):
        require_admin()
        values = {} if values is None else values
        if not isinstance(values, dict):
            raise ValueError('Invalid diagnostic inputs')
        if action == 'email':
            if set(values) != {'sender', 'recipients'}:
                raise ValueError('Choose sender and recipient emails')
            sender, recipients = values['sender'], values['recipients']
            if any(not isinstance(value, str) or len(value) > 4096 or any(c in value for c in '\r\n\0')
                   for value in (sender, recipients)):
                raise ValueError('Invalid email address')
            addresses = [value.strip() for value in recipients.split(',') if value.strip()]
            if not sender.strip() or '@' not in sender or not 1 <= len(addresses) <= 100 or any('@' not in value for value in addresses):
                raise ValueError('Choose sender and recipient emails')
            mailserver = Config.get_value('services', 'mailserver')
            if not mailserver:
                raise ValueError('No mail server is configured')
            from pyasm.command import EmailTriggerTestCmd
            command = EmailTriggerTestCmd(sender_email=sender.strip(), recipient_emails=addresses,
                                          msg='Simple Email Test by TACTIC')
            command.set_mailserver(mailserver)
            Command.execute_cmd(command)
            return dict(message='Email sent successfully')
        if action == 'script':
            if set(values) != {'path'} or not isinstance(values['path'], str) or not values['path'].strip() or len(values['path']) > 4096 or '\0' in values['path']:
                raise ValueError('Please enter a valid script path')
            from tactic.command import PythonCmd
            Command.execute_cmd(PythonCmd(script_path=values['path']))
            return dict(message='Script completed')
        raise ValueError('Unknown System Info test')
