"""Real temporary projects exercise progress cards and related-task contracts."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.common import Config
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from scripts.task_cells_contract import exercise_related


class ProcessProgressTests(unittest.TestCase):
    def test_legacy_object_completion_and_related_navigation(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
                os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
            Config.reload_config()
            store = Store(Path(directory)/'sqlite')
            store.initialize(hash_password('isolated-progress-test'))
            api = Api(store)
            ticket = api.get_ticket('admin', 'isolated-progress-test')
            exercise_related(api, ticket)
