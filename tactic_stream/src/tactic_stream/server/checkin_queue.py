"""Authenticated multipart chunks and batched results for native queue check-ins."""
import json

from pyasm.command import Command
from tactic.command.checkin_queue_cmd import SubmitCheckinChunkCmd, CancelCheckinBatchCmd, updates

FIELDS = {'batch_id', 'chunk_id', 'operations', 'pieces', 'batches', 'cursors'}


def checkin_queue_request(action, payload, uploads=None):
    from tactic_stream.server.api import Api
    from pyasm.common import Config, Environment
    from pyasm.common.errors import SecurityException
    if action == 'updates':
        Api.check_method_access('query')
        return updates(payload.get('batches', []), payload.get('cursors', {}))
    if action == 'submit':
        arguments = {key: payload.get(key) for key in ('batch_id', 'chunk_id')}
        for key in ('operations', 'pieces'):
            value = payload.get(key, [])
            arguments[key] = json.loads(value) if isinstance(value, str) else value
        arguments['uploads'] = uploads or []
        command = SubmitCheckinChunkCmd(**arguments)
    elif action == 'cancel':
        command = CancelCheckinBatchCmd(batch_id=payload.get('batch_id'))
    else:
        raise ValueError('Unknown check-in queue action')
    command.get_transaction().set_sync(False)
    name = command.__class__.__module__ + '.' + command.__class__.__name__
    Api.check_method_access('execute_cmd', command=name)
    if Config.get_value('security', 'api_cmd_restricted') == 'true' and not Environment.get_security().check_access('api_cmd', name, 'allow', default='allow'):
        raise SecurityException('Check-in queue command access denied')
    return Command.execute_cmd(command)
