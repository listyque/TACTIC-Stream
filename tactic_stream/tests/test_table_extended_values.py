"""Compare added value cells with executable original widget methods."""

import ast
import calendar
import json
import unittest
from datetime import UTC, datetime
from types import MethodType, SimpleNamespace
from unittest.mock import patch

from dateutil import parser
from test_table_value_widgets import LEGACY

from pyasm.common import jsonloads
from pyasm.search.search import RequestContext, request_context
from tactic.ui.table.snapshot_element_wdg import (
    SnapshotFileElementWdg,
    SnapshotLockedElementWdg,
)
from tactic.ui.table.statistic_wdg import TaskDaysDueElementWdg, TaskGroupCompletionWdg
from tactic.ui.table.subcontext_wdg import SubContextElementWdg
from tactic_stream.server.table_cells import describe_cell, safe_link


def methods(file, name, names):
    tree = ast.parse((LEGACY / file).read_text(encoding="utf-8"))
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == name
    )
    scope = {
        "six": SimpleNamespace(string_types=(str,)),
        "parser": parser,
        "jsonloads": jsonloads,
    }
    for method in cls.body:
        if isinstance(method, ast.FunctionDef) and method.name in names:
            exec(
                compile(ast.Module(body=[method], type_ignores=[]), file, "exec"), scope
            )
    return {name: scope[name] for name in names}


class ExtendedTableValues(unittest.TestCase):
    def test_action_on_boolean_field_remains_an_action(self):
        descriptor = describe_cell(
            {
                "name": "enabled",
                "display": {
                    "handler": "tactic.ui.table.CheckinButtonElementWdg",
                    "options": {},
                },
                "action": {"handler": "", "options": {}},
            },
            {"enabled": {"data_type": "boolean"}},
        )
        self.assertTrue(descriptor["supported"])
        self.assertEqual(descriptor["kind"], "checkin")

    def test_older_completion_filters_obsolete_processes(self):
        from pyasm.widget.statistic_wdg import TaskCompletionWdg
        from tactic.ui.table.statistic_wdg import TaskCompletionWdg as Modern

        parent = object()
        tasks = [
            SimpleNamespace(get_value=lambda key, value=value: value)
            for value in ("model", "obsolete")
        ]
        pipeline = SimpleNamespace(get_process_names=lambda recurse: ["model"])
        widget = TaskCompletionWdg(name="completion")
        with (
            patch.object(Modern, "get_tasks", return_value=tasks),
            patch("pyasm.biz.Pipeline.get_by_sobject", return_value=pipeline),
        ):
            self.assertEqual(widget.get_tasks(parent), tasks[:1])
        widget.get_tasks = lambda sobject: tasks[:1]
        widget.get_status_attr = lambda task: SimpleNamespace(
            get_percent_completion=lambda: 66.7
        )
        self.assertEqual(widget.get_completion(parent), 66)

    def setUp(self):
        context = request_context(RequestContext(None, "admin"))
        context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)

    def test_subcontext_keeps_nested_server_labels(self):
        original = methods(
            "tactic/ui/table/subcontext_wdg.py",
            "SubContextElementWdg",
            ["_get_subcontext"],
        )["_get_subcontext"]
        for value in ["", "publish", "publish/daily/review", "модель/тест"]:
            widget = SubContextElementWdg(name="subcontext")
            widget.set_sobjects([SimpleNamespace(get_value=lambda key: value)])
            self.assertEqual(widget.get_cell_value()["text"], original(widget))

    def test_due_labels_and_thresholds_match_original(self):
        original = methods(
            "tactic/ui/table/statistic_wdg.py",
            "TaskDaysDueElementWdg",
            ["get_value", "init_data", "get_text_value"],
        )

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 17, 12)

        for delta in [None, -200000, -3600, 0, 1800, 4000, 10000, 200000]:
            for status in ["", "Done", None]:
                utc = (
                    None
                    if delta is None
                    else datetime.fromtimestamp(
                        calendar.timegm(Clock.now().timetuple()) + delta, UTC
                    ).replace(tzinfo=None)
                )
                record = SimpleNamespace(
                    get_value=lambda key: status if key == "status" else utc
                )
                widget = TaskDaysDueElementWdg(name="due")
                widget.set_sobjects([record])
                baseline = SimpleNamespace(
                    get_current_sobject=lambda: record,
                    due_date_col="bid_end_date",
                    get_option=lambda key: "",
                    DAY=86400,
                    HOUR=3600,
                )
                for name, method in original.items():
                    setattr(baseline, name, MethodType(method, baseline))
                with patch("datetime.datetime", Clock):
                    self.assertEqual(
                        widget.get_cell_value()["text"], baseline.get_text_value()
                    )

    def test_locks_share_one_lookup_per_parent_context(self):
        values = {"search_type": "cg/assets", "search_id": 1, "context": "publish"}
        rows = [
            SimpleNamespace(get_value=values.get, get_parent=lambda: "parent")
            for _ in range(2)
        ]
        widget = SnapshotLockedElementWdg(name="locked")
        widget.set_sobjects(rows)
        with patch("pyasm.biz.Snapshot.is_locked", return_value=True) as lookup:
            widget.preprocess()
            self.assertEqual(lookup.call_count, 1)
            self.assertEqual(
                widget.get_cell_value(), {"text": "Locked", "checked": True}
            )

    def test_snapshot_file_preserves_filename_and_sequence(self):
        widget = SnapshotFileElementWdg(name="file")
        widget.set_sobjects(
            [
                SimpleNamespace(
                    is_insert=lambda: False,
                    get_web_path_by_type=lambda: "/assets/frames.####.exr",
                    get_value=lambda key: "sequence",
                    get_file_range=lambda: SimpleNamespace(get_display=lambda: "1-100"),
                )
            ]
        )
        self.assertEqual(
            widget.get_cell_value(),
            {"text": "frames.####.exr (1-100)", "href": "/assets/frames.####.exr"},
        )
        self.assertEqual(safe_link("javascript:alert(1)"), "")

    def test_group_completion_uses_original_context_average(self):
        original = methods(
            "tactic/ui/table/statistic_wdg.py",
            "TaskGroupCompletionWdg",
            ["get_group_completion", "calculate", "get_text_value"],
        )
        tasks = [
            SimpleNamespace(get_value=lambda key, value=value: value)
            for value in ["model", "rig", "model"]
        ]
        widget = TaskGroupCompletionWdg(
            name="completion",
            options=json.dumps(
                [
                    {"label": "MODEL", "context": ["model"]},
                    {"label": "EMPTY", "context": []},
                ]
            ),
        )
        widget.set_sobjects([SimpleNamespace(get_id=lambda: 1)])
        widget.is_preprocessed = True
        widget.group_list = json.loads(widget.get_option("options"))
        values = {id(tasks[0]): 0, id(tasks[1]): 50, id(tasks[2]): 100}
        widget.get_tasks = lambda obj: tasks
        widget.get_completion = lambda task: values[id(task)]
        baseline = SimpleNamespace(
            group_list=widget.group_list,
            get_tasks=widget.get_tasks,
            get_completion=widget.get_completion,
            get_current_sobject=widget.get_current_sobject,
        )
        for name, method in original.items():
            setattr(baseline, name, MethodType(method, baseline))
        self.assertEqual(widget.get_cell_value()["text"], baseline.get_text_value())
        self.assertEqual(widget.get_cell_value()["groups"][0]["completion"], 50)

    def test_descriptors_reject_unknown_options_and_do_not_require_fake_db_fields(self):
        for name, kind in [
            ("SnapshotLockedElementWdg", "locked"),
            ("SnapshotFileElementWdg", "link"),
            ("MilestoneCompletionWdg", "completion"),
            ("TaskGroupCompletionWdg", "group_completion"),
            ("TaskDaysDueElementWdg", "text"),
            ("SubContextElementWdg", "text"),
        ]:
            element = {
                "name": "computed",
                "display": {"handler": "tactic.ui.table." + name, "options": {}},
                "action": {"handler": ""},
            }
            descriptor = describe_cell(element, {})
            self.assertTrue(descriptor["supported"] and descriptor["server"], name)
            self.assertEqual(descriptor["kind"], kind)
            self.assertFalse(descriptor["sortable"])
            element["display"]["options"]["cbjs_action"] = "never execute"
            self.assertFalse(describe_cell(element, {})["supported"])


if __name__ == "__main__":
    unittest.main()
