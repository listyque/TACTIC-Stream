from pyasm.command.command import Command, CommandException, CommandExitException, HandlerCmd
from pyasm.command.trigger import Trigger, TriggerException, SnapshotIsLatestTrigger

__all__ = ["Command", "CommandException", "CommandExitException", "HandlerCmd", "Trigger", "TriggerException"]
__all__.append("SnapshotIsLatestTrigger")
__all__ += ['Workflow', 'WorkflowException', 'BaseWorkflowNodeHandler', 'BaseProcessTrigger',
            'ProcessStatusTrigger', 'CustomProcessConfig', 'WorkflowManualNodeHandler']


def __getattr__(name):
    if name in ('DatabaseAction', 'DefaultValueDatabaseAction', 'MultiDatabaseAction',
                'NonEmptyAction', 'RegexAction', 'NullAction', 'UniqueValueAction', 'XmlAction', 'UploadAction', 'MultiUploadAction', 'MultiZipUploadAction', 'DateAction', 'TimeAction', 'TaskDateAction', 'InitialTaskCreateAction'):
        from . import edit_wdg_action
        return getattr(edit_wdg_action, name)
    if name in ('UndoCmd', 'RedoCmd'):
        from . import undo_cmd
        return getattr(undo_cmd, name)
    if name in ('ColumnAddCmd', 'ColumnDropCmd'):
        from . import database_cmd
        return getattr(database_cmd, name)
    if name in ('Workflow', 'WorkflowException', 'BaseWorkflowNodeHandler', 'BaseProcessTrigger',
                'ProcessStatusTrigger', 'CustomProcessConfig', 'WorkflowManualNodeHandler'):
        from . import workflow
        return getattr(workflow, name)
    raise AttributeError(name)

from .file_upload import FileUpload, FileUploadException
__all__ += ['FileUpload', 'FileUploadException']

__all__ += ['ColumnAddCmd', 'ColumnDropCmd']

__all__ += ['UndoCmd', 'RedoCmd']
__all__ += ['DatabaseAction', 'DefaultValueDatabaseAction', 'MultiDatabaseAction',
            'NonEmptyAction', 'RegexAction', 'NullAction', 'UniqueValueAction', 'XmlAction', 'UploadAction', 'MultiUploadAction', 'MultiZipUploadAction', 'DateAction', 'TimeAction', 'TaskDateAction', 'InitialTaskCreateAction']
