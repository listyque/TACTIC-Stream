"""Configured inline forms use native EditCmd and its ordinary transaction journal."""

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchType
from tactic.ui.panel import EditCmd
from tactic_stream.dashboard_plan import dashboard_from_xml
from tactic_stream.server.dashboard_fields import form
from tactic_stream.server.dashboards import dashboard_layout
from tactic_stream.server.navigation_links import check_project
from .agent_request_cmd import selected_object


class DashboardFormCmd(Command):
    def execute(self):
        check_project(Project.get_project_code())
        action = self.kwargs.get("action")
        if action not in ("save", "check"):
            raise ValueError("Choose Save or Check for this form")
        view, path = self.kwargs.get("view"), self.kwargs.get("path")
        if (
            not isinstance(view, str)
            or not view.startswith("dashboard.")
            or not isinstance(path, list)
            or not 1 <= len(path) <= 7
            or any(type(index) is not int or not 0 <= index < 32 for index in path)
        ):
            raise ValueError("Choose a saved page form")
        if action == "save":
            for search_type in ("config/widget_config",):
                sql = Search(search_type).get_sql()
                sql.get_database_impl().lock_collection_table(
                    sql, SearchType.get(search_type).get_table()
                )
        query = Search("config/widget_config")
        query.add_filter("view", view)
        records = query.get_sobjects()
        if len(records) != 1:
            raise ValueError("Choose a saved page form")
        document = dashboard_from_xml(records[0].get_value("config"), view[10:])
        children, in_details = document.blocks, False
        for index in path:
            if index >= len(children):
                raise ValueError("Reload the changed page before saving")
            block = children[index]
            in_details = in_details or block.kind == "details"
            children = block.children
        if block.kind != "form":
            raise ValueError("Choose a saved page form")
        detail_key = self.kwargs.get("detail_key", "")
        if bool(detail_key) != in_details:
            raise ValueError("Select the record for this form")
        context = (
            selected_object(detail_key)
            if detail_key
            else (
                selected_object(self.kwargs["search_key"])
                if self.kwargs.get("search_key")
                else Project.get()
            )
        )
        source = (
            selected_object(block.source_key)
            if block.source_key
            else (Project.get() if block.binding == "project" else context)
        )
        if block.search_type and source.get_base_search_type() != block.search_type:
            raise ValueError("The record belongs to another data source")
        if action == "save":
            sql = source.get_sql()
            sql.get_database_impl().lock_collection_table(sql, source.get_table())
            source = selected_object(source.get_search_key())
        prepared = form(block, source)
        if prepared["readOnly"]:
            raise SecurityException("This form is read-only")
        if prepared["configRevision"] != self.kwargs.get("config_revision"):
            raise ValueError("The form configuration changed. Reload before saving.")
        values = self.kwargs.get("values")
        fields = {
            item["name"]: item for item in prepared["fields"] if not item["readOnly"]
        }
        if (
            not isinstance(values, dict)
            or not values
            or set(values) - fields.keys()
            or any(
                not isinstance(value, (str, int, float, bool, type(None)))
                for value in values.values()
            )
        ):
            raise ValueError("Choose editable fields from this form")
        if any(
            isinstance(value, str) and len(value) > 65536 for value in values.values()
        ):
            raise ValueError("Form text exceeds 64 KiB")
        converted = {}
        for name, value in values.items():
            field = fields[name]
            if field["type"] == "bool":
                if not isinstance(value, bool):
                    raise ValueError("Choose Yes or No")
                value = "on" if value else ""
            elif field["type"] == "select":
                if value not in [item["value"] for item in field["options"]]:
                    raise ValueError("Choose an available field value")
            elif field["type"] in ("date", "datetime-local"):
                value = (
                    field["unchanged"]
                    if value == field["value"]
                    else (value + field["suffix"] if value else "")
                )
            if field["required"] and value in ("", None):
                raise ValueError("Complete the required fields")
            converted[name] = value
        expected = self.kwargs.get("expected_revision")
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("Reload the form before saving")
        command = EditCmd(
            search_key=source.get_search_key(),
            view=block.edit_view,
            data=converted,
            expected_revision=expected,
            action=action,
        )
        Command.execute_cmd(command)
        state = command.info.get("state", "saved")
        model = dashboard_layout(
            document,
            view,
            self.kwargs.get("search_key", ""),
            detail_key=detail_key,
            filter_values=self.kwargs.get("filter_values"),
        )
        return dict(state=state, model=model)
