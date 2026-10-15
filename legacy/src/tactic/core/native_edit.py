"""JSON value adapter around the ORIGINAL EditCmd and field action sequence.

Only a plain DatabaseAction is adapted; custom/default/action handlers retain
upstream semantics. Legacy EditCmd callers are not changed.
"""
from .edit_commands import EditCmd
from pyasm.command.edit_wdg_action import DatabaseAction
from pyasm.common import UserException

class ExplicitDatabaseAction(DatabaseAction):
    def get_values(self,name=None):
        if self.value: return [self.value]
        if name and name!=self.name and hasattr(self,'explicit_values'):
            return [self.explicit_values.get(name,'')]
        return [self.explicit_value]
    def check(self):
        if self.explicit_value is None and self.get_option('empty') == 'false':
            raise UserException('Поле не может быть пустым: '+self.name)
        return super().check()
    def convert_value(self,col_type,value):
        if col_type in ('integer','float') and value == 0 and type(value) is not bool:
            return 0 if col_type=='integer' else 0.0
        return super().convert_value(col_type,value)
    def execute(self):
        if self.explicit_value is None and not self.get_option('expression') and self.get_option('parent_key')!='true':
            self.sobject.set_value(self.get_option('column') or self.name, None, allow_none=True)
            if self.commit_flag:self.sobject.commit()
        else:
            super().execute()

from pyasm.command.edit_wdg_action import TaskDateAction, NonEmptyAction

class ExplicitTaskDateAction(ExplicitDatabaseAction, TaskDateAction):
    """Keep TaskDateAction.postprocess while transporting explicit JSON values."""
    pass

class ExplicitNonEmptyAction(ExplicitDatabaseAction, NonEmptyAction):
    def check(self):
        return NonEmptyAction.check(self)

class NativeEditCmd(EditCmd):
    def _get_action_handlers(self):
        handlers=super()._get_action_handlers()
        for index,handler in enumerate(handlers):
            if type(handler) in (DatabaseAction, TaskDateAction, NonEmptyAction) and self.data is not None and handler.name in self.data:
                adapted=({TaskDateAction:ExplicitTaskDateAction,NonEmptyAction:ExplicitNonEmptyAction}.get(type(handler),ExplicitDatabaseAction))()
                adapted.__dict__.update(handler.__dict__)
                adapted.explicit_value=self.data[handler.name]
                handlers[index]=adapted
        return handlers

# The original actions sometimes read sibling fields through WebContainer (e.g.
# LoginAction.license_type and PasswordAction confirmation). A JSON request has
# no HTML form body, so make only the validated values visible during execute.
# Restore the original request even when a validator or trigger raises.
from contextlib import contextmanager

@contextmanager
def validated_form_values(values):
    from pyasm.web import WebContainer
    web=WebContainer.get_web()
    form=web.get_form_data() if hasattr(web,'get_form_data') else None
    if not isinstance(form,dict):
        yield
        return
    original=dict(form)
    try:
        form.update({k:('on' if v is True else '' if v is False or v is None else v) for k,v in values.items()})
        if 'password_reenter' in values:form['password re-enter']=values['password_reenter']
        yield
    finally:
        form.clear();form.update(original)

from pyasm.command.edit_wdg_action import PasswordAction

class ExplicitPasswordAction(PasswordAction):
    def get_values(self,name=None):
        name=name or self.name
        if name=='password re-enter' and name not in self.explicit_values:
            name='password_reenter'
        return [self.explicit_values.get(name,'')]

# Preserve the original command and override input transport only.
_OriginalNativeEditCmd=NativeEditCmd
class NativeEditCmd(_OriginalNativeEditCmd):
    def execute(self):
        with validated_form_values(self.data or {}):
            return super().execute()
    def _get_action_handlers(self):
        handlers=super()._get_action_handlers()
        for index,handler in enumerate(handlers):
            if isinstance(handler,ExplicitDatabaseAction):handler.explicit_values=self.data or {}
            if type(handler) is PasswordAction and self.data is not None and handler.name in self.data:
                adapted=ExplicitPasswordAction();adapted.__dict__.update(handler.__dict__)
                adapted.explicit_values=self.data;handlers[index]=adapted
        return handlers


from .edit_commands import EditMultipleCmd

class NativeTableEditMultipleCmd(EditMultipleCmd):
    """Original batch algorithm/events; only its validated input transport differs."""
    edit_command_class = NativeEditCmd
