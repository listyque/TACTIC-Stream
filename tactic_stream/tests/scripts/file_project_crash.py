"""Owned child used to kill a native request before/after its database commit."""
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

from pyasm.biz.file_project import COMMAND, FileProjectRecord
from pyasm.search.storage import Store
from pyasm.search.transaction import Transaction
from tactic_stream.server.api import Api

data = json.loads(sys.stdin.read())
api = Api(Store(Path(data['directory'])))
action = data['kwargs']['action']
original_trigger = FileProjectRecord._call_triggers
original_commit = Transaction.commit


def trigger(record, *args, **kwargs):
    kind = record.get_base_search_type()
    target = {'upload_chunk': 'blob', 'edit': 'version', 'submit': 'change'}[action]
    if not data['after_commit'] and kind == 'file_project/' + target:
        os._exit(73)
    return original_trigger(record, *args, **kwargs)


def commit(transaction):
    result = original_commit(transaction)
    if data['after_commit'] and not transaction.is_in_transaction():
        os._exit(74)
    return result


with patch.object(FileProjectRecord, '_call_triggers', trigger), patch.object(Transaction, 'commit', commit):
    api.dispatch('execute_cmd', (data['ticket'], COMMAND, data['kwargs']))
raise AssertionError('Crash injection did not fire')
