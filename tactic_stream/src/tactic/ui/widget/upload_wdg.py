# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Original single-file upload context and form handoff, without JavaScript."""
from pyasm.biz import Snapshot
from pyasm.widget import BaseInputWdg, SelectWdg, TextWdg, InputException
from pyasm.common.errors import UnsupportedContract

__all__ = ['SimpleUploadWdg', 'UploadWdg']


class SimpleUploadWdg(BaseInputWdg):
    def __init__(self, **kwargs):
        name = kwargs.get('key')
        super().__init__(name, 'upload', **kwargs)

    def get_input(self):
        if self.kwargs.get('client_action'):
            raise UnsupportedContract('Client-side immediate upload actions are not migrated')
        self.context = self.kwargs.get('context')
        if not self.context:
            current = self.get_current_sobject()
            self.context = current.get_icon_context() if current else Snapshot.get_default_context()
        return self


class UploadWdg(SimpleUploadWdg):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.show_upload = False

    ARGS_KEYS = {
        'context': {
            'description': 'context dropdown list for check-in. e.g. icon|publish|special',
            'type': 'TextWdg', 'order': 2, 'category': 'Optional',
        },
        'client_action': {
            'description': "For server side action in Edit Panel, choose empty and set 'UploadAction' in the action field",
            'type': 'SelectWdg', 'values': 'icon_checkin|submission',
            'order': 1, 'category': 'Optional',
        },
    }

    def get_input(self):
        super().get_input()
        # Business branches from original get_info_wdg; HTML/JS stays excluded.
        context_option = self.kwargs.get('context')
        context_expr_option = self.kwargs.get('context_expr')
        pipeline_option = self.kwargs.get('pipeline') in ['true', True, 'True']
        setting_option = self.kwargs.get('setting')
        context_name = '%s|context' % self.get_input_name()
        self.subcontext = bool(context_expr_option or context_option or setting_option)
        if self.subcontext:
            text = SelectWdg(context_name)
            text.set_sobject(self.get_current_sobject())
            if context_expr_option:
                text.set_option('values_expr', context_expr_option)
            elif context_option:
                text.set_option('values', context_option)
            elif setting_option:
                text.set_option('setting', setting_option)
        elif pipeline_option:
            from pyasm.biz import Pipeline
            pipeline = Pipeline.get_by_sobject(self.get_current_sobject())
            if not pipeline:
                raise InputException('Upload context requires an object pipeline')
            text = SelectWdg(context_name)
            text.set_option('values', pipeline.get_process_names(recurse=True))
        else:
            text = TextWdg(context_name)
        self.context_input = text
        self.upload_fields = [dict(name=self.name, required=self.get_option('required') in (True, 'true'))]
        return self
