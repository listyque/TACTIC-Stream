"""UI controls for the current administrator's project-scoped executor."""
from pathlib import Path
import time

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.security.security import _require_admin
from pyasm.search import Search


class AgentExecutorCmd(Command):
    @staticmethod
    def snapshot():
        from tactic_stream import agent_runtime as runtime
        from .agent_request_cmd import AgentRequestCmd, HOST_TTL
        from tactic_stream.server.agent_desktops import targets, BUSY
        desktops = targets(Project.get_project_code())
        value = runtime.state(runtime.directory(Environment.get_data_dir(), Environment.get_user_name(), Project.get_project_code()))
        external = False
        if value['state'] not in runtime.BUSY and not any(row['state'] in BUSY for row in desktops):
            reader = AgentRequestCmd()
            reader.owner, reader.sql = Environment.get_user_name(), Search('config/trigger').get_sql()
            if reader.sql.table_exists('spt_agent_host') and any(time.time() - host['seen'] <= HOST_TTL for host in reader.records('spt_agent_host')):
                external = True
        choices = desktops + [dict(id='server', kind='server', label='TACTIC server', **value)]
        if external:
            choices.append(dict(id='external', kind='external', label='External agent', state='external', error='', managed=False))
        selected = next((row for row in choices if row['state'] in (*BUSY, 'external')), None)
        if not selected and len(desktops) == 1:
            selected = desktops[0]
        return dict(selected or dict(state='stopped', error='', managed=False),
                    target=selected['id'] if selected else '', targets=choices)

    def execute(self):
        _require_admin()
        project = Project.get_project_code()
        if self.kwargs.get('project_code') != project:
            raise ValueError('Agent executor project mismatch')
        action = self.kwargs.get('action')
        if action not in ('state', 'start', 'stop', 'desktop_poll'):
            raise ValueError('Unknown agent executor action')
        if action == 'desktop_poll':
            from tactic_stream.server.agent_desktops import poll
            self.info = poll(self.kwargs)
            return
        from pyasm.common.config import config_file_lock
        from tactic_stream.server.agent_desktops import path
        file = path().with_suffix('.control')
        file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with config_file_lock(file):
            self.control(action, project)

    def control(self, action, project):
        from tactic_stream import agent_runtime as runtime
        scope = runtime.directory(Environment.get_data_dir(), Environment.get_user_name(), project)
        target = self.kwargs.get('target')
        if action in ('start', 'stop') and not target:
            raise ValueError('Choose the computer that will run the agent')
        if action in ('start', 'stop') and target != 'server':
            from tactic_stream.server.agent_desktops import control, BUSY
            current = self.snapshot()
            control(target, project, action, unavailable=any(row['state'] in (*BUSY, 'external')
                and row['id'] != target for row in current['targets']))
            self.info = self.snapshot()
            return
        if action == 'start':
            if any(row['id'] != 'server' and row['state'] in ('preparing', *runtime.BUSY, 'external') for row in self.snapshot()['targets']):
                raise ValueError('An external agent is already connected to this project')
            from tactic_stream.server.startup import read_server_config
            settings = read_server_config(Environment.get_data_dir())
            host = settings['host']
            host = '127.0.0.1' if host == '0.0.0.0' else '::1' if host == '::' else host
            server = 'http://%s:%s' % ('[%s]' % host if ':' in host else host, settings['port'])
            root = Path(runtime.__file__).resolve().parents[2]
            handler = root.parents[1] / 'TH'
            self.info = runtime.start(scope, server, project, Environment.get_ticket(), root,
                                      handler if (handler / 'thlib').is_dir() else None)
        elif action == 'stop':
            self.info = runtime.stop(scope)
        else:
            self.info = self.snapshot()
