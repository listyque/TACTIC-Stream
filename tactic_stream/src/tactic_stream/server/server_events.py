"""Web workers distribute the single collector feed without querying the database."""
import asyncio
import json
import logging
import os
from pathlib import Path
import time
from uuid import uuid4
from pyasm.common.file_io import read_text, write_text


class ServerEvents:
    def __init__(self, data_dir, interval=.5):
        self.feed = Path(data_dir) / 'cache' / 'update-feed.json'
        self.alive = self.feed.with_suffix('.alive')
        self.subscribers = []
        self.task = None
        self.versions = {}
        self.stamp = None
        self.committed = {}
        self.start_lock = asyncio.Lock()
        self.interval = interval
        self.clients_file = self.feed.parent / 'event-clients' / ('%s-%s.json' % (os.getpid(), uuid4().hex))
        self.clients_dirty = False
        self.clients_at = 0
        self.clients_write = None

    def read_changes(self):
        if time.time() - self.alive.stat().st_mtime > 5:
            raise OSError('Update collector heartbeat expired')
        stat = self.feed.stat()
        stamp = stat.st_mtime_ns, stat.st_ino
        if self.stamp == stamp:
            return set()
        records = json.loads(read_text(self.feed))
        versions = {(project, search_type, login): revision for project, search_type, login, revision, committed in records}
        self.committed = {(project, search_type, login): committed for project, search_type, login, revision, committed in records}
        changes = {key for key, revision in versions.items() if self.versions.get(key) != revision}
        self.versions = versions
        self.stamp = stamp
        return changes

    async def subscribe(self, project, subscription, client=None):
        async with self.start_lock:
            if not self.subscribers:
                self.stamp = None
                await asyncio.to_thread(self.read_changes)
            if self.task is None or self.task.done():
                self.task = asyncio.create_task(self.watch())
            subscriber = dict(project=project or 'sthpw', subscription=subscription, since=time.time_ns(), event=asyncio.Event(), changes=set())
            subscriber['client'] = dict(client or {}, connection=uuid4().hex)
            self.subscribers.append(subscriber)
            self.clients_dirty = True
        return subscriber

    def unsubscribe(self, subscriber):
        try:
            self.subscribers.remove(subscriber)
        except ValueError:
            return
        self.clients_dirty = True

    def write_clients(self, rows):
        self.clients_file.parent.mkdir(parents=True, exist_ok=True)
        write_text(self.clients_file, json.dumps(dict(updated=time.time(), clients=rows)))

    async def watch(self):
        while True:
            await asyncio.sleep(self.interval)
            try:
                if self.clients_dirty or (self.subscribers and time.monotonic() - self.clients_at >= 20):
                    rows = [dict(item['client'], worker=os.getpid(), login=item['subscription'].get('login', ''),
                                 project=item['project'], connected_at=item['since'] / 1e6,
                                 channels=item['subscription']['channels'], search_types=item['subscription']['search_types'])
                            for item in self.subscribers]
                    self.clients_dirty = False
                    self.clients_write = asyncio.create_task(asyncio.to_thread(self.write_clients, rows))
                    await asyncio.shield(self.clients_write)
                    self.clients_at = time.monotonic()
                if not self.subscribers:
                    continue
                async with self.start_lock:
                    changes = await asyncio.to_thread(self.read_changes)
            except (OSError, ValueError):
                logging.getLogger(__name__).exception('Server event watcher stopped; clients must resynchronise')
                for subscriber in self.subscribers:
                    subscriber['error'] = True
                    subscriber['event'].set()
                return
            for subscriber in self.subscribers:
                relevant = {item for item in changes if self.committed[item] > subscriber['since'] and matching_changes(subscriber, {item})['channels']}
                if relevant:
                    subscriber['changes'].update(relevant)
                    subscriber['event'].set()

    async def close(self):
        if self.task is not None:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        if self.clients_write is not None:
            await self.clients_write
        self.clients_file.unlink(missing_ok=True)


def read_event_clients(data_dir):
    """Admin-only worker snapshots; no tickets, per-client queries or presence guesses."""
    rows = []
    for path in (Path(data_dir) / 'cache' / 'event-clients').glob('*.json'):
        try:
            snapshot = json.loads(read_text(path))
            # A crashed worker cannot remove its file; ignore its expired lease.
            if time.time() - snapshot['updated'] <= 45:
                rows.extend(snapshot['clients'])
        except (OSError, ValueError, KeyError):
            continue
    return sorted(rows, key=lambda row: (row['login'], row['connected_at']))


def matching_changes(subscriber, changes):
    subscription = subscriber['subscription']
    channels, types = set(), set()
    for project, search_type, login in changes:
        if login and login != subscription.get('login'):
            continue
        if project not in ('sthpw', subscriber['project']):
            continue
        if project == 'sthpw' and search_type in ('sthpw/message', 'sthpw/message_log', 'sthpw/subscription'):
            channels.update(set(subscription['channels']) & {'messages', 'reactions'})
        if project == subscriber['project'] and 'activity' in subscription['channels']:
            channels.add('activity')
        if 'cache' in subscription['channels'] and search_type in subscription['search_types']:
            channels.add('cache')
            types.add(search_type)
    return {'channels': sorted(channels), 'search_types': sorted(types)}


def advance_cursors(payload, result):
    for name, rows in [('message_after', result['messages']), ('activity_after', result['activity'])]:
        times = [row.get('__event_timestamp__') or row.get('timestamp') for row in rows]
        if any(times):
            payload[name] = max(value for value in times if value)
    for name, field in [('reaction_after', 'reactionCursor'), ('cache_after', 'cacheCursor')]:
        if result.get(field):
            payload[name] = result[field]


def presence_state(result):
    return sorted((row['login'], row['online']) for row in result.get('presence', []))


def event_frame(event, data):
    return 'event: ' + event + '\ndata: ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n\n'
