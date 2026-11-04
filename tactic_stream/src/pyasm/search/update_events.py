"""Commit wake-ups shared by local workers; native journals remain the source of data."""
from hashlib import sha256
import json
import logging
import os
import time
import zlib
from pathlib import Path
from uuid import uuid4
from pyasm.common.file_io import write_text, replace
from pyasm.biz.file_bytes import byte_lock
from pyasm.common.file_io import read_text

PROJECT_TYPES = {
    'sthpw/task', 'sthpw/note', 'sthpw/snapshot', 'sthpw/file', 'sthpw/work_hour',
    'sthpw/connection', 'sthpw/status_log', 'sthpw/pipeline', 'sthpw/schema', 'sthpw/search_object',
}


def publish_changes(data_dir, changes):
    directory = Path(data_dir) / 'cache' / 'update-events'
    directory.mkdir(parents=True, exist_ok=True)
    for change in set(changes):
        project, search_type, *audience = change
        login = audience[0] if audience else ''
        name = sha256(('\0'.join((project, search_type, login))).encode()).hexdigest()
        temporary = directory / (name + '.' + uuid4().hex + '.pending')
        now = time.time_ns()
        write_text(temporary, json.dumps([project, search_type, uuid4().hex, login, now]), fsync=False)
        try:
            target = directory / (name + '.json')
            with byte_lock(target):
                try:
                    existing_ts = json.loads(read_text(target))[-1] if target.exists() else -1
                except (ValueError, TypeError, IndexError):
                    existing_ts = -1
                if existing_ts > now:
                    temporary.unlink()
                else:
                    replace(temporary, target)
        except OSError:
            # The collector retries this complete, durable publication after commit.
            logging.getLogger(__name__).exception('Committed notification retained for delivery: %s', temporary.name)


def capture_change(sobject):
    from pyasm.search.transaction import Transaction
    transaction = Transaction.get()
    if transaction is not None and transaction.notify_updates:
        # Keep the final native row, including project/recipients; never query at commit.
        transaction.update_objects[(sobject.get_search_type(), sobject.get_id())] = sobject


def publish_transaction(transaction):
    if not transaction.notify_updates:
        return
    from pyasm.search.search import _context
    from pyasm.biz import Project
    from pyasm.common import Xml
    context = _context.get(None)
    if context is None:
        return
    types = {row.get_value('search_type') for row in transaction.change_timestamps.values()}
    types.update(Xml.get_attribute(node, 'search_type') for node in transaction.xml.get_nodes('transaction/sobject'))
    changes = set()
    recipients = {}
    message_ids = {}
    for (search_type, _), row in transaction.update_objects.items():
        base = search_type.split('?', 1)[0]
        if base == 'sthpw/message_log':
            message_ids[row.get_id()] = row.get_value('message_code')
            try:
                metadata = row.get_json_value('metadata', default={}, no_exception=True)
            except (ValueError, TypeError, zlib.error):
                metadata = {}
            delivery = metadata.get('delivery', {}) if isinstance(metadata, dict) else {}
            if isinstance(delivery, dict) and isinstance(delivery.get('recipients'), dict):
                logins = set(delivery['recipients'])
                sender = delivery.get('sender') or row.get_value('login', no_exception=True)
                if isinstance(sender, str):
                    logins.add(sender)
                recipients.setdefault(row.get_value('message_code'), set()).update(value for value in logins if isinstance(value, str) and value)
    captured = set()
    for (search_type, _), row in transaction.update_objects.items():
        base = search_type.split('?', 1)[0]
        project = 'sthpw' if base.startswith('sthpw/') else row.get_project_code()
        if base in PROJECT_TYPES:
            project = row.get_value('project_code', no_exception=True) or project
        logins = {''}
        if base in ('sthpw/message', 'sthpw/message_log'):
            conversation = row.get_value('message_code' if base.endswith('message_log') else 'code', no_exception=True)
            logins = recipients.get(conversation, logins)
        elif base == 'sthpw/subscription':
            logins = {row.get_value('login', no_exception=True) or ''}
        elif base == 'sthpw/connection' and row.get_value('context', no_exception=True) == 'chat_attachment':
            for prefix in ('src_', 'dst_'):
                if str(row.get_value(prefix + 'search_type', no_exception=True)).split('?', 1)[0] == 'sthpw/message_log':
                    logins = recipients.get(message_ids.get(row.get_value(prefix + 'search_id')), logins)
        changes.update((project, base, login) for login in logins)
        captured.add(base)
    for search_type in types - {None, ''}:
        base = search_type.split('?', 1)[0]
        if base in captured:
            continue
        if base in transaction.notify_excluded_types:
            continue
        # Tickets are transport state; expiry/revocation is checked on heartbeat.
        if base in ('sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp', 'sthpw/ticket'):
            continue
        # System objects can be changed from any project's command context.
        project = 'sthpw' if base.startswith('sthpw/') else Project.get_project_code()
        if '?project=' in search_type:
            from urllib.parse import parse_qs
            project = parse_qs(search_type.partition('?')[2]).get('project', [project])[0]
        changes.add((project, base, ''))
    excluded = transaction.notify_excluded_types | {'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp', 'sthpw/ticket'}
    changes = {change for change in changes if change[1] not in excluded}
    if changes:
        try:
            publish_changes(context.store.data_dir, changes)
        except Exception:
            # The data is committed: never make the caller retry a successful write.
            logging.getLogger(__name__).exception('Committed changes could not notify SSE clients; reconnect to resynchronise')
