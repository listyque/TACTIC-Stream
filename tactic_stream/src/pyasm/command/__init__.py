from pyasm.command.command import Command, CommandException, CommandExitException, HandlerCmd
from pyasm.command.trigger import Trigger, TriggerException, SnapshotIsLatestTrigger

__all__ = ["Command", "CommandException", "CommandExitException", "HandlerCmd", "Trigger", "TriggerException"]
__all__.append("SnapshotIsLatestTrigger")
__all__ += ['Workflow', 'WorkflowException', 'BaseWorkflowNodeHandler', 'BaseProcessTrigger',
            'ProcessStatusTrigger', 'CustomProcessConfig', 'WorkflowManualNodeHandler']
__all__ += ['EmailTrigger', 'EmailTrigger2', 'EmailTriggerThread', 'SendEmail', 'EmailTriggerTest', 'EmailTriggerTestCmd']
__all__ += ['EmailHandler', 'TaskAssignEmailHandler', 'NoteEmailHandler', 'GeneralNoteEmailHandler',
            'GeneralPublishEmailHandler', 'TaskStatusEmailHandler', 'TestEmailHandler']
__all__ += ['SubprocessTrigger', 'QueueTrigger', 'ScriptTrigger']


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
    if name in ('EmailTrigger', 'EmailTrigger2', 'EmailTriggerThread', 'SendEmail', 'EmailTriggerTest', 'EmailTriggerTestCmd'):
        from . import email_trigger
        return getattr(email_trigger, name)
    if name in ('EmailHandler', 'TaskAssignEmailHandler', 'NoteEmailHandler', 'GeneralNoteEmailHandler',
                'GeneralPublishEmailHandler', 'TaskStatusEmailHandler', 'TestEmailHandler'):
        from . import email_handler
        return getattr(email_handler, name)
    if name in ('SubprocessTrigger', 'QueueTrigger', 'ScriptTrigger'):
        from . import subprocess_trigger
        return getattr(subprocess_trigger, name)
    raise AttributeError(name)

from .file_upload import FileUpload, FileUploadException
__all__ += ['FileUpload', 'FileUploadException']

__all__ += ['ColumnAddCmd', 'ColumnDropCmd']

__all__ += ['UndoCmd', 'RedoCmd']
__all__ += ['DatabaseAction', 'DefaultValueDatabaseAction', 'MultiDatabaseAction',
            'NonEmptyAction', 'RegexAction', 'NullAction', 'UniqueValueAction', 'XmlAction', 'UploadAction', 'MultiUploadAction', 'MultiZipUploadAction', 'DateAction', 'TimeAction', 'TaskDateAction', 'InitialTaskCreateAction']
