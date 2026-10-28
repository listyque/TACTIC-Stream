"""Bound page forms use native permissions, revisions, recovery and Undo."""

import unittest
from uuid import uuid4
from xmlrpc.client import Fault
import test_transport


class RecordParts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.url = test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_native_form_save_conflicts_recovery_and_undo(self):
        with test_transport.Transport.proxy(self) as proxy:
            auth = dict(
                ticket=proxy.get_ticket("admin", "private-test-password"), project="one"
            )
            config = proxy.insert(
                auth,
                "config/widget_config",
                dict(
                    search_type="contract/entity",
                    view="record_parts_edit",
                    config='<config><record_parts_edit><element name="name"/><element name="amount"/></record_parts_edit></config>',
                ),
            )

            def call(action, **values):
                return proxy.execute_cmd(
                    auth,
                    "tactic.ui.panel.dashboard_cmd.DashboardCmd",
                    dict(action=action, project_code="one", **values),
                )["info"]

            key = "contract/entity?project=one&code=A"
            document = dict(
                name="record_parts",
                title="Record parts",
                blocks=[
                    dict(
                        kind="field",
                        title="Progress",
                        binding="record",
                        source_key=key,
                        field="amount",
                        format="progress",
                    ),
                    dict(
                        kind="form",
                        title="Native fields",
                        binding="record",
                        source_key=key,
                        fields=["name", "amount"],
                        edit_view="record_parts_edit",
                    ),
                    dict(
                        kind="action",
                        title="Edit",
                        binding="record",
                        source_key=key,
                        native_action="edit",
                    ),
                ],
            )
            revision = call("read")["revision"]
            model = call("preview", document=document, expected_revision=revision)[
                "model"
            ]
            self.assertEqual(model["layoutNodes"][0]["value"], 0)
            form = model["layoutNodes"][1]["form"]
            self.assertEqual(
                [row["name"] for row in form["fields"]], ["name", "amount"]
            )
            self.assertEqual(form["fields"][1]["value"], 0)
            call(
                "apply",
                document=document,
                expected_revision=revision,
                operation_id=str(uuid4()),
            )
            args = dict(
                form["scope"],
                expected_revision=form["expectedRevision"],
                config_revision=form["configRevision"],
                values=dict(name="Edited in page", amount="12"),
            )

            def edit(action, **changes):
                return proxy.execute_cmd(
                    auth,
                    "tactic.ui.panel.dashboard_form_cmd.DashboardFormCmd",
                    dict(args, action=action, **changes),
                )["info"]

            with self.assertRaises(Fault):
                edit("save", path=[0])
            with self.assertRaises(Fault):
                edit("save", values=dict(code="CHANGE"))
            saved = edit("save")
            self.assertEqual(saved["state"], "saved")
            self.assertEqual(
                proxy.get_by_search_key(auth, key)["name"], "Edited in page"
            )
            self.assertEqual(saved["model"]["layoutNodes"][0]["value"], 12)
            with test_transport.Transport.store.connection() as db:
                transaction = db.execute(
                    "SELECT id FROM transaction_log ORDER BY id DESC LIMIT 1"
                ).fetchone()[0]
            with self.assertRaises(Fault):
                edit("save")
            self.assertEqual(edit("check")["state"], "saved")
            proxy.undo(auth, None, transaction)
            self.assertEqual(proxy.get_by_search_key(auth, key)["amount"], 0)
            self.assertNotEqual(
                proxy.get_by_search_key(auth, key)["name"], "Edited in page"
            )
            proxy.update(auth, key, dict(name="Other editor"))
            self.assertEqual(edit("check")["state"], "conflict")
            with self.assertRaises(Fault):
                edit("save")
            proxy.update(
                auth,
                config["__search_key__"],
                dict(
                    config='<config><record_parts_edit><element name="name"/><element name="amount" title="Changed"/></record_parts_edit></config>'
                ),
            )
            with self.assertRaises(Fault):
                edit("save")
            from pyasm.security.authenticator import hash_password

            proxy.insert(
                auth,
                "sthpw/login",
                dict(
                    login="form_viewer",
                    password=hash_password("private-viewer-password"),
                ),
            )
            proxy.insert(
                auth,
                "sthpw/login_group",
                dict(
                    code="form_viewers",
                    login_group="form_viewers",
                    access_level="none",
                    namespace="one",
                    project_code="one",
                    access_rules='<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="contract/entity" access="view"/></rules>',
                ),
            )
            proxy.insert(
                auth,
                "sthpw/login_in_group",
                dict(login="form_viewer", login_group="form_viewers"),
            )
            viewer = dict(
                ticket=proxy.get_ticket("form_viewer", "private-viewer-password"),
                project="one",
            )
            readonly = proxy.execute_cmd(
                viewer,
                "tactic.ui.table.CustomLayoutReadCmd",
                dict(view="dashboard.record_parts"),
            )["info"]
            self.assertTrue(readonly["layoutNodes"][1]["form"]["readOnly"])
            self.assertFalse(readonly["layoutNodes"][2]["available"])
            proxy.insert(
                auth,
                "config/widget_config",
                dict(
                    search_type="CustomLayoutWdg",
                    category="CustomLayoutWdg",
                    view="legacy_private",
                    config='<config><view name="legacy_private"><mako>raise RuntimeError("Must never execute")</mako><html>Private layout</html></view></config>',
                ),
            )
            with self.assertRaises(Fault) as denied:
                proxy.execute_cmd(
                    viewer,
                    "tactic.ui.table.CustomLayoutReadCmd",
                    dict(view="legacy_private"),
                )
            self.assertEqual(denied.exception.faultString, "Permission denied")
            with self.assertRaises(Fault):
                proxy.execute_cmd(
                    viewer,
                    "tactic.ui.table.CustomLayoutReadCmd",
                    dict(view="dashboard.record_parts", html="<div>forbidden</div>"),
                )
            with self.assertRaises(Fault):
                proxy.execute_cmd(
                    viewer,
                    "tactic.ui.panel.dashboard_form_cmd.DashboardFormCmd",
                    dict(args, action="save"),
                )
            self.assertEqual(proxy.get_by_search_key(auth, key)["name"], "Other editor")
            proxy.insert(
                auth,
                "sthpw/login",
                dict(
                    login="form_editor",
                    password=hash_password("private-editor-password"),
                ),
            )
            proxy.insert(
                auth,
                "sthpw/login_group",
                dict(
                    code="form_editors",
                    login_group="form_editors",
                    namespace="one",
                    project_code="one",
                    access_level="none",
                    access_rules='<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="contract/entity" access="edit"/></rules>',
                ),
            )
            proxy.insert(
                auth,
                "sthpw/login_in_group",
                dict(login="form_editor", login_group="form_editors"),
            )
            editor = dict(
                ticket=proxy.get_ticket("form_editor", "private-editor-password"),
                project="one",
            )
            model = proxy.execute_cmd(
                editor,
                "tactic.ui.table.CustomLayoutReadCmd",
                dict(view="dashboard.record_parts"),
            )["info"]
            edit_form = model["layoutNodes"][1]["form"]
            self.assertFalse(edit_form["readOnly"])
            edited = proxy.execute_cmd(
                editor,
                "tactic.ui.panel.dashboard_form_cmd.DashboardFormCmd",
                dict(
                    edit_form["scope"],
                    action="save",
                    expected_revision=edit_form["expectedRevision"],
                    config_revision=edit_form["configRevision"],
                    values=dict(name="Edited by member"),
                ),
            )["info"]
            self.assertEqual(edited["state"], "saved")
            self.assertEqual(
                proxy.get_by_search_key(auth, key)["name"], "Edited by member"
            )
            with test_transport.Transport.store.connection() as db:
                own_transaction = db.execute(
                    "SELECT id FROM transaction_log ORDER BY id DESC LIMIT 1"
                ).fetchone()[0]
            proxy.undo(editor, None, own_transaction)
            self.assertEqual(proxy.get_by_search_key(auth, key)["name"], "Other editor")
            for block in [
                dict(
                    kind="field",
                    binding="record",
                    source_key="contract/entity?project=two&code=A",
                    field="name",
                ),
                dict(
                    kind="field",
                    binding="record",
                    source_key=key,
                    field="name",
                    format="progress",
                ),
                dict(kind="action", native_action="arbitrary_execute"),
            ]:
                with self.assertRaises(Fault):
                    call(
                        "preview",
                        document=dict(
                            name="invalid_parts", title="Invalid", blocks=[block]
                        ),
                        expected_revision=call("read")["revision"],
                    )
