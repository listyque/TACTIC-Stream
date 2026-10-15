"""TEST-ONLY update_multi observer, registered only in a disposable database."""
import json
from pathlib import Path
from pyasm.command import Trigger
from pyasm.common import Environment
from pyasm.search import SearchType
class GridAuditTrigger(Trigger):
    def execute(self):
        if not (Path(Environment.get_data_dir())/'.native-real-test').is_file():
            raise RuntimeError('GridAuditTrigger must never run on user data')
        row=SearchType.create('sthpw/debug_log')
        row.set_value('category','native-grid-012')
        row.set_value('message',json.dumps(self.get_input(),ensure_ascii=False,default=str))
        row.commit()
