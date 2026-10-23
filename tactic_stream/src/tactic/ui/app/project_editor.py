"""Project lifecycle through the original EditCmd field-action boundary."""

from pyasm.command.edit_wdg_action import DatabaseAction
from pyasm.common import UserException


class ProjectArchiveAction(DatabaseAction):
    def check(self):
        self.change_lifecycle = False
        if not super().check():
            return False
        if self.sobject.get_base_search_type() != "sthpw/project":
            raise UserException("Project lifecycle requires a project")
        if self.sobject.get_code() in ("admin", "sthpw"):
            raise UserException("Built-in system projects cannot be archived")
        value = self.get_value(self.name)
        if value not in (None, "", "retired"):
            raise UserException("Invalid project lifecycle value")
        self.was_archived = self.sobject.get_value("s_status") == "retired"
        self.archive = value == "retired"
        self.change_lifecycle = self.was_archived != self.archive
        return True

    def execute(self):
        # EditCmd commits ordinary fields before invoking lifecycle triggers.
        pass

    def postprocess(self):
        if not self.change_lifecycle:
            return
        if self.archive:
            self.sobject.retire()
        else:
            self.sobject.reactivate()
