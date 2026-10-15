"""Native HTML output compared with the actual original embedded runtime."""
import test_read_parity as reads
from pyasm.search.search import RequestContext, request_context
from tools.snapshot_probe import run_snapshot_case

class HtmlParity(reads.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='html_api_contract', name='native_html', project='admin')]

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            return run_snapshot_case(case)
