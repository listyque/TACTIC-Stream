"""One monitored producer coalesces native transaction signals for all clients."""
import json
import logging
import multiprocessing
import os
from pathlib import Path
import time
from uuid import uuid4
from pyasm.common.file_io import read_text, write_text, replace
from pyasm.biz.file_bytes import byte_lock


class UpdateCollector:
    def __init__(self, data_dir):
        self.directory = Path(data_dir) / 'cache' / 'update-events'
        self.directory.mkdir(parents=True, exist_ok=True)
        self.feed = self.directory.parent / 'update-feed.json'
        self.alive = self.directory.parent / 'update-feed.alive'
        self.stamps = {}
        self.revisions = {}
        self.dirty = True

    def tick(self):
        changed = self.dirty or not self.feed.exists()
        seen = set()
        for path in [*self.directory.glob('*.json'), *self.directory.glob('*.pending')]:
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            seen.add(path)
            stamp = (stat.st_mtime_ns, stat.st_ino)
            if self.stamps.get(path) == stamp:
                continue
            try:
                value = read_text(path)
            except FileNotFoundError:
                seen.discard(path)
                continue
            try:
                project, search_type, revision, *audience = json.loads(value)
                committed = int(audience[1]) if len(audience) > 1 else stat.st_mtime_ns
            except (ValueError, TypeError, IndexError):
                path.unlink(missing_ok=True)
                seen.discard(path)
                self.stamps.pop(path, None)
                continue
            key = project, search_type, audience[0] if audience else ''
            if self.revisions.get(key, ('', 0))[1] > committed:
                self.stamps[path] = stamp
                continue
            changed |= self.revisions.get(key, (None,))[0] != revision
            self.revisions[key] = revision, committed
            self.stamps[path] = stamp
        if len(self.stamps) > len(seen):
            self.stamps = {path: stamp for path, stamp in self.stamps.items() if path in seen}
        self.dirty = changed
        if changed:
            try:
                write_text(self.feed, json.dumps([(*key, *value) for key, value in sorted(self.revisions.items())]))
                self.dirty = False
            except PermissionError:
                logging.getLogger(__name__).exception('Update feed replacement deferred')
        if not self.dirty:
            for path in self.directory.glob('*.pending'):
                try:
                    # Keep the canonical record for collector restarts; never replace a newer revision.
                    target = path.with_name(path.name.split('.')[0] + '.json')
                    try:
                        pending = json.loads(read_text(path))
                        pending_ts = int(pending[-1])
                    except (ValueError, TypeError, IndexError):
                        path.unlink(missing_ok=True)
                        self.stamps.pop(path, None)
                        continue
                    with byte_lock(target):
                        try:
                            target_ts = int(json.loads(read_text(target))[-1]) if target.exists() else -1
                        except (ValueError, TypeError, IndexError):
                            target_ts = -1
                        if target_ts > pending_ts:
                            path.unlink()
                        else:
                            replace(path, target)
                        self.stamps.pop(path, None)
                except (PermissionError, BlockingIOError, FileNotFoundError):
                    continue
        self.alive.touch()


def start_updates(settings, heartbeat=None, stop=None):
    """The monitor owns restart/shutdown; no database or user payload is cached."""
    collector = UpdateCollector(settings['data_dir'])
    parent = multiprocessing.parent_process()
    while not (stop is not None and stop.value) and not (parent and not parent.is_alive()):
        try:
            collector.tick()
            if heartbeat is not None:
                heartbeat.value = time.monotonic()
        except (OSError, ValueError):
            logging.getLogger(__name__).exception('Update collector failed')
            raise
        time.sleep(settings.get('update_interval', .5))
