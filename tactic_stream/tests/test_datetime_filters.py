"""Native timestamp filters compare instants, retaining microseconds and UTC offsets."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


class DatetimeFilters(unittest.TestCase):
    def test_native_sqlite_timestamp_filters(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('datetime-test-password'))
            with store.connection(write=True) as db:
                for code, timestamp in [('BEFORE', '2030-01-01 12:00:00.123455 +0000'),
                        ('SAME', '2030-01-01 15:00:00.123456 +0300'), ('AFTER', '2030-01-01 12:00:00.123457')]:
                    db.execute('INSERT INTO note (code, timestamp, access, project_code) VALUES (?, ?, ?, ?)',
                        (code, timestamp, 'public', 'admin'))
            api = Api(store)
            ticket = api.get_ticket('admin', 'datetime-test-password')
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', ticket)
                for value in ('2030-01-01 12:00:00.123456Z', '2030-01-01 15:00:00.123456+03:00',
                        datetime(2030, 1, 1, 12, 0, 0, 123456, timezone.utc)):
                    for op, expected in [('=', ['SAME']), ('>', ['AFTER']), ('>=', ['AFTER', 'SAME']),
                            ('<', ['BEFORE']), ('<=', ['BEFORE', 'SAME']), ('!=', ['AFTER', 'BEFORE'])]:
                        search = Search('sthpw/note')
                        search.add_filter('timestamp', value, op=op)
                        self.assertEqual(sorted(row.get_code() for row in search.get_sobjects()), expected, (op, value))


if __name__ == '__main__':
    unittest.main()
