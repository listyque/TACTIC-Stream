# Copyright (c) 2009, Southpaw Technology. See LICENSE.TACTIC.
"""Configured Python REST delegates to the existing API/PythonCmd checks."""
from tactic.ui.common import BaseRefreshWdg


class PythonRestHandler(BaseRefreshWdg):
    def get_display(self):
        from tactic_client_lib import TacticServerStub
        arguments = dict(self.kwargs)
        path = arguments.pop('script_path', None)
        if not path:
            raise ValueError('Python REST requires a configured script_path')
        return TacticServerStub.get(protocol='local').execute_python_script(path, arguments)['info']
