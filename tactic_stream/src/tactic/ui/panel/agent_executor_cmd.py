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
        value = runtime.state(runtime.directory(Environment.get_data_dir(), Environment.get_user_name(), Project.get_project_code()))
        if value['state'] not in runtime.BUSY:
            reader = AgentRequestCmd()
            reader.owner, reader.sql = Environment.get_user_name(), Search('config/trigger').get_sql()
            if reader.sql.table_exists('spt_agent_host') and any(time.time() - host['seen'] <= HOST_TTL for host in reader.records('spt_agent_host')):
                return dict(state='external', error='', managed=False)
        return value

    def execute(self):
        _require_admin()
        project = Project.get_project_code()
        if self.kwargs.get('project_code') != project:
            raise ValueError('Agent executor project mismatch')
        action = self.kwargs.get('action')
        if action not in ('state', 'start', 'stop'):
            raise ValueError('Unknown agent executor action')
        from tactic_stream import agent_runtime as runtime
        scope = runtime.directory(Environment.get_data_dir(), Environment.get_user_name(), project)
        if action == 'start':
            if self.snapshot()['state'] == 'external':
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
