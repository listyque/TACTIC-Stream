# Copyright (c) 2009 Southpaw Technology. See LICENSE.TACTIC.
"""Original task assignment group expressions, without HTML/Sudo."""
from pyasm.biz import Pipeline
from pyasm.widget import BaseInputWdg, SelectWdg
from pyasm.common.errors import UnsupportedContract


class ProcessGroupSelectWdg(BaseInputWdg):
    ARGS_KEYS = {'label_attr': {'description': 'a list of | seperated login attributes to show in place of just the login attribute',
                              'type': 'TextWdg', 'order': 0, 'category': 'Display'}}

    def get_input(self):
        from tactic.ui.panel import EditWdg
        if not isinstance(self.get_parent_wdg(), EditWdg):
            raise UnsupportedContract('Inline assignment group switching is not migrated')
        self.labels_attr = self.get_option('label_attr').split('|') if self.get_option('label_attr') else ['display_name']
        sobject = self.get_current_sobject()
        parent = sobject.get_parent()
        pipeline_code = parent.get_value('pipeline_code', no_exception=True) if parent else None
        pipeline = Pipeline.get_by_code(pipeline_code)
        group = None
        if pipeline:
            attrs = pipeline.get_process_attrs(sobject.get_value('process'))
            group = attrs.get('%s_login_group' % self.get_name())
        if group:
            values_expr = "@GET(sthpw/login_group['login_group', '%s'].sthpw/login_in_group.sthpw/login.login)" % group
            labels_expr = ["@GET(sthpw/login_group['login_group', '%s'].sthpw/login_in_group.sthpw/login.%s)" % (group, x.strip()) for x in self.labels_attr]
        else:
            values_expr = '@GET(sthpw/login.login)'
            labels_expr = ['@GET(sthpw/login.%s)' % x.strip() for x in self.labels_attr]
        select = SelectWdg(self.get_input_name())
        select.add_empty_option('-- Select a User --')
        select.set_option('values_expr', values_expr)
        select.set_option('labels_expr', ' + &nbsp + '.join(labels_expr))
        current_value = sobject.get_value(self.get_name())
        if current_value:
            select.set_value(current_value)
        return select

    # Original method returns the prepared SelectWdg, also read by Handler scripts.
    get_display = get_input
