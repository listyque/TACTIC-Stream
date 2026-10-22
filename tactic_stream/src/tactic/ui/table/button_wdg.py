# Copyright (c) 2005-2008 Southpaw Technology. See LICENSE.TACTIC.
"""Original configured button resolution; clients retain script/UI execution."""

from pyasm.biz import ExpressionParser
from pyasm.search import Search
from tactic.ui.common import BaseTableElementWdg
import re


class ButtonElementWdg(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys(('script_path', 'script_code', 'script', 'path', 'javascript',
        'cbjs_action', 'icon', 'hint', 'icon_tip', 'enable', 'expression', 'color', 'size', 'align'), {})

    def preprocess(self):
        self.script_obj = None
        code = self.get_option('script_code') or self.get_option('script')
        path = self.get_option('path') or self.get_option('script_path')
        if code or path:
            search = Search('config/custom_script')
            if code:
                search.add_filter('code', code)
            else:
                folder, _, title = str(path).rpartition('/')
                search.add_filter('folder', folder)
                search.add_filter('title', title)
            rows = search.get_sobjects()
            if len(rows) != 1:
                raise ValueError('Select one existing custom script')
            self.script_obj = rows[0]

    def is_editable(self):
        return False

    def is_sortable(self):
        return False

    def get_cell_value(self):
        obj = self.get_current_sobject()
        if not obj or obj.is_insert():
            return dict(text='', actions=[])
        enabled = self.get_option('enable')
        if enabled and not ExpressionParser().eval(enabled, obj):
            return dict(text='', actions=[])
        icon = ExpressionParser().eval(self.get_option('icon'), obj) if self.get_option('icon') else 'create'
        expression = self.get_option('expression')
        value = ExpressionParser().eval(expression, obj) if expression else None
        text = '' if value is None else str(value)
        inline = self.get_option('cbjs_action') or self.get_option('javascript')
        source = getattr(self, 'script_obj', None)
        if not inline and source is None:
            raise ValueError('No script defined for this button')
        size = str(self.get_option('size') or '17').removesuffix('px')
        if not size.isdecimal() or not 12 <= int(size) <= 28:
            raise ValueError('Table button icon size must be between 12 and 28 pixels')
        color = ExpressionParser().eval(self.get_option('color'), obj) if self.get_option('color') else ''
        if color and not re.fullmatch(r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?:[0-9a-fA-F]{2})?', str(color)):
            raise ValueError('Table button color must be a hexadecimal color')
        return dict(text=text, columnName=self.get_name(), align=self.get_option('align') or 'center', targetSearchKey=obj.get_search_key(),
                    scriptKey=source.get_search_key() if source else '',
                    scriptLanguage=(source.get_value('language') if source else '') or 'javascript',
                    actions=[dict(name='script', label=self.get_option('icon_tip') or self.get_option('hint') or 'Run script',
                                  icon=str(icon), iconSize=int(size), iconColor=str(color), iconAction=True,
                                  translateLabel=not bool(self.get_option('icon_tip') or self.get_option('hint')))])
