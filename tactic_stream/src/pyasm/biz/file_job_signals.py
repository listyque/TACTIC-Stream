"""Bounded cross-process telemetry/cancellation for an atomic database command."""
import json
import os
from pathlib import Path
import uuid


class FileJobSignals:
    def __init__(self, data_dir, project, task):
        self.directory = Path(data_dir) / 'temp' / 'file-jobs' / project / task

    def cancelled(self):
        return (self.directory / 'cancel').is_file()

    def cancel(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / 'cancel').touch()

    def progress(self, value):
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.directory / (uuid.uuid4().hex + '.tmp')
        try:
            temporary.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
            os.replace(temporary, self.directory / 'progress.json')
        finally:
            temporary.unlink(missing_ok=True)

    def read(self):
        try:
            with (self.directory / 'progress.json').open('rb') as stream:
                raw = stream.read(16385)
            if len(raw) > 16384:
                return {}
            value = json.loads(raw)
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def clear(self):
        for name in ('cancel', 'progress.json'):
            (self.directory / name).unlink(missing_ok=True)
        try:
            self.directory.rmdir()
        except OSError:
            pass
