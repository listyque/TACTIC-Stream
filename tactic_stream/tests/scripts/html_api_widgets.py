"""Actual project-defined Widget classes used by the XML-RPC contract tests."""
from pyasm.web import DivWdg, WebContainer
from tactic.ui.common import BaseRefreshWdg


class EchoWdg(BaseRefreshWdg):
    def get_display(self):
        div = DivWdg()
        div.add_style('color', div.get_color('color'))
        if self.kwargs.get('gradient'):
            div.add_gradient('background', 'background')
        div.add(self.kwargs.get('text', ''))
        div.add(WebContainer.get_web().get_form_value('value'))
        return div


class BrokenWdg(BaseRefreshWdg):
    def init(self):
        from tactic_client_lib import TacticServerStub
        TacticServerStub.get(protocol='local').insert('sthpw/note', {'note': 'render must roll back'})
        raise ValueError('render failed after write')
