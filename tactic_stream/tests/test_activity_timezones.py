"""Real HTTP/XML-RPC boundaries: UTC instants, local days and DST counts."""
import ast
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import test_transport
from tactic_stream.server.activity_query import query_user_recent_activity


class ActivityTimezones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.url = test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_utc_headers_local_calendar_and_dst_on_both_query_paths(self):
        instants = ("2026-03-08 04:59:59", "2026-03-08 05:00:00",
                    "2026-03-09 03:59:59", "2026-03-09 04:00:00",
                    "2026-11-01 03:59:59", "2026-11-01 04:00:00",
                    "2026-11-02 04:59:59", "2026-11-02 05:00:00")
        with test_transport.Transport.store.connection(write=True) as db:
            for index, timestamp in enumerate(instants):
                db.execute("INSERT INTO note (code,project_code,search_type,search_code,process,note,login,access,timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
                           (f"TZ{index}", "one", "contract/entity", "A", "publish", "Time zone boundary", "admin", "public", timestamp))
                db.execute('INSERT INTO transaction_log (code,login,namespace,timestamp,"transaction") VALUES (?,?,?,?,?)',
                           (f"TZLOG{index}", "admin", "one", timestamp,
                            '<transaction><sobject search_type="contract/entity" search_code="A" action="update"><column name="name" from="Old" to="New"/></sobject></transaction>'))
        handler = Path(__file__).resolve().parents[3] / "TH/thlib/tactic_query.py"
        source = handler.read_text(encoding="utf-8")
        node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "query_user_recent_activity")
        sources = [inspect.getsource(query_user_recent_activity), ast.get_source_segment(source, node)]
        with test_transport.Transport.proxy(self) as proxy:
            ticket = proxy.get_ticket("admin", "private-test-password")
            def call(**values):
                request = Request(test_transport.Transport.url + "/admin/activity-feed",
                                  data=json.dumps(dict(ticket=ticket, project="one", **values)).encode(),
                                  headers={"Content-Type": "application/json"})
                before = datetime.now(timezone.utc)
                with urlopen(request) as response:
                    start = datetime.fromisoformat(response.headers['X-Tactic-UTC-Started'])
                    end = datetime.fromisoformat(response.headers['X-Tactic-UTC-Ended'])
                    self.assertLessEqual(before, start)
                    self.assertLessEqual(start, end)
                    self.assertLessEqual(end, datetime.now(timezone.utc))
                    return json.load(response)["result"]
            for zone, day, wanted in (("America/New_York", "2026-03-08", [1, 2]),
                                      ("Europe/Moscow", "2026-03-08", [0, 1]),
                                      ("UTC", "2026-03-09", [2, 3]),
                                      ("Pacific/Auckland", "2026-03-09", [2, 3]),
                                      ("America/New_York", "2026-11-01", [5, 6])):
                for kind in ("note", "change"):
                    with self.subTest(zone=zone, kind=kind):
                        for query in sources:
                            code = query + "\nreturn query_user_recent_activity(project_code='one', kinds=%r, day=%r, time_zone=%r, include_day_counts=True)" % ([kind], day, zone)
                            result = proxy.execute_python_script(dict(ticket=ticket, project="one"), "", dict(code=code))["info"]
                            self.assertEqual(sorted(row["timestamp"] for row in result["records"]), [instants[i] for i in wanted])
                            counts = {row["dateKey"]: row["count"] for row in result["dayCounts"]}
                            self.assertEqual(counts[day], 2)
                            self.assertEqual(sum(counts.values()), 8)
                records = call(filter="notes", day=day, time_zone=zone)["records"]
                self.assertEqual(sorted(row["timestamp"] for row in records), [instants[i] for i in wanted])
                self.assertTrue(all(row["dayKey"] == day for row in records))
                counts = call(filter="notes", counts_only=True, time_zone=zone)["dayCounts"]
                self.assertEqual(next(row["count"] for row in counts if row["dateKey"] == day), 2)
            for bad in ("../UTC", "No/SuchZone", [], 3):
                with self.assertRaises(HTTPError) as failure:
                    call(time_zone=bad)
                self.assertEqual(failure.exception.code, 400)
                failure.exception.close()


if __name__ == "__main__":
    unittest.main()
