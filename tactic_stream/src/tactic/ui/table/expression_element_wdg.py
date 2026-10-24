###########################################################
#
# Copyright (c) 2005-2008, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

"""Native expression values from TACTIC; DOM and JavaScript rendering excluded."""
import ast
import datetime
from copy import copy

from pyasm.common import Container, FormatValue, SPTDate
from pyasm.search import Search, SearchKey
from pyasm.biz import ExpressionParser
from pyasm.command import Command
from tactic.ui.common import SimpleTableElementWdg


class ExpressionElementWdg(SimpleTableElementWdg):
    """General purpose element widget for expressions."""

    ARGS_KEYS = {
        'expression': {
            'description': 'Expression to evaluate the widget',
            'type': 'TextAreaWdg',
            'order': 1,
            'category': 'Options'
        },
        'display_expression': {
            'description': 'Expression for display purposes',
            'type': 'TextAreaWdg',
            'order': 2,
            'category': 'Options'
        },
        'display_format': {
            'description': 'Predefined format for display',
            'type': 'TextWdg',
            'order': 3,
            'category': 'Options'
        },
        'link_expression': {
            'description': 'Expression for linking to another sobject',
            'type': 'TextAreaWdg',
            'order': 4,
            'category': 'Options',
        },
        'link_view': {
            'description': 'View to link result to another view',
            'type': 'TextWdg',
            'order': 5,
            'category': 'Options',
        },
        'inline_styles': 'Styles to add to the DIV generated that contains the result of the expression',
        'return':   {
            'descripton' : 'Determines what the expression return type should be',
            'type': 'SelectWdg',
            'values': 'single|list'
        },
        'bottom':   {
            'description': 'Expression to calculate the bottom row of the table',
            'type': 'TextAreaWdg',
        },
        'group_bottom':   {
            'description': 'Expression to calculate the bottom of a group',
            'type': 'TextAreaWdg',
        },
        'mode':     {
            'description': 'Display mode for this widget',
            'type': 'SelectWdg',
            'values': 'value|check|boolean',
            'order': 3
    
        },
        'expression_mode':     {
            'description': 'If absolute mode is selected, it does not relate to the current SObject',
            'type': 'SelectWdg',
            'values': 'default|absolute',
            'order': 6
    
        },
        'calc_mode':     {
            'description': '(ALPHA) fast|slow - fast uses new calculation mode. Only @SUM, @COUNT, @SOBJECT and @GET are current supported',
            'type': 'SelectWdg',
            'values': 'slow|fast',
            'order': 7
        },
    
        'show_retired':     {
            'description': 'true|false - true shows all the retired entries during the expression evaluation',
            'type': 'SelectWdg',
            'values': 'true|false',
            'category': 'Options',
            'order': 8
        },
    
    
        'enable_eval_listener': {
            'description': '''Currently javascript expression evaluation is not fully baked, so only use the client side evaluation listener when needed and NOT by default''',
            'category': 'internal'
        ,
        },
        'use_cache':     {
            'description': 'Determines whether or not to use the cached value.  Gets value from column with the same name as the element',
            'type': 'SelectWdg',
            'values': 'true|false',
            'order': 0,
            'category': 'Cache'
        },
        'order_by': {
            'description': 'Turn on Order by',
            'type': 'TextWdg',
            
            'order': 8,
            'category': 'Options'
        },
         'group_by': {
            'description': 'Turn on Group by',
            'type': 'SelectWdg',
            'values': 'true|false',
            'order': 9,
            'category': 'Options'
        },
        
         'group_by_time': {
            'description': 'Turn on Group by',
            'type': 'SelectWdg',
            'values': 'true|false',
            'order': 10,
            'category': 'Options'
        },
    
        'justify': {
            'description': 'Result justification',
            'type': 'SelectWdg',
            'values': 'default|left|right|center',
            'order': 11,
            'category': 'Options'
        },
        'filter_name': {
            'description': 'Name of filter to use',
            'type': 'TextWdg',
            'order': 12,
            'category': 'Options'
        },
    
        'empty': {
            'description': "vAlue to display if empty"
        }
    
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.init()

    def init(self):
        self.td = None
        self.expression = self.alt_expression = self.alt_result = self.report_value = None
        self.cache_results = {}

    def set_sobjects(self, sobjects, search=None):
        super().set_sobjects(sobjects, search)
        self.cache_results = {}

    def set_option(self, key, value):
        super().set_option(key, value)
        self.cache_results = {}

    def set_options(self, options):
        super().set_options(options)
        self.cache_results = {}

    def preprocess(self):
        order_by = self.get_option('order_by')
        expression = self.get_option('expression')
        if not order_by or order_by == 'true':
            if expression.startswith('@GET(') and expression.endswith(')') and expression.count('@') == 1:
                # lstrip('@GET(') in the source also stripped letters from column names.
                self.set_option('order_by', expression[5:-1].strip().lstrip('.'))
        self.init_kwargs()

    def init_kwargs(self):
        state = self.get_option('state')
        if state and state.get('parent_key'):
            self.sobject = SearchKey.get_by_search_key(state['parent_key'])
        self.expression = self.get_option('expression')
        self.alt_expression = self.get_option('alt_expression')
        self.mode = self.get_option('mode') or 'value'
        self.show_retired = self.get_option('show_retired') in (True, 'true')
        self.enable_eval_listener = self.get_option('enable_eval_listener') in (True, 'true', 'True', 'TRUE')

    def get_required_columns(self):
        return []

    def is_sortable(self):
        if self.get_option('use_cache') in (True, 'true'):
            return True
        order_by = self.get_option('order_by')
        return bool(order_by and order_by != 'false' and 'connect' not in order_by.split('.'))

    def is_groupable(self):
        return self.get_option('use_cache') in (True, 'true') or self.get_option('group_by') in (True, 'true')

    def is_time_groupable(self):
        return self.get_option('group_by_time') in (True, 'true')

    def is_editable(self):
        return 'optional'

    def get_vars(self):
        self.vars = {'ELEMENT_NAME': self.get_name()}
        self.vars.update(Container.get('Message:search_vars') or {})
        return self.vars

    def _get_result(self, sobject, expression):
        """Original native expression calculation, without implicit Sudo or eval."""
        name = self.get_name()
        if self.get_option('data_mode') == 'report' or self.get_option('use_cache') in (True, 'true'):
            return sobject.get_value(name)
        if sobject is not None and not isinstance(sobject, list) and sobject.is_insert():
            return ''
        self.vars = {'ELEMENT_NAME': name, 'ELEMENT': name,
                     'SOBJECT_ID': sobject.get_id() if sobject is not None else None,
                     'SOBJECT_CODE': sobject.get_code() if sobject is not None else None}
        ret_list = self.get_option('return') == 'list'
        absolute = self.get_option('expression_mode') == 'absolute'
        # The fast dictionary belongs to this widget/page only. Row-dependent
        # variables cannot use a dictionary calculated with the first row's vars.
        fast = self.get_option('calc_mode') == 'fast' and not absolute and not any(
            var in expression for var in ('$SOBJECT_ID', '$SOBJECT_CODE'))
        if fast:
            if expression not in self.cache_results:
                results = ExpressionParser().eval(expression, self.sobjects, vars=self.vars,
                                      dictionary=True, show_retired=self.show_retired)
                if isinstance(results, str):
                    results = ast.literal_eval(results) if results else {}
                if not isinstance(results, dict):
                    raise ValueError('Fast expression calculation must return a dictionary')
                self.cache_results[expression] = results
            result = self.cache_results[expression].get(sobject.get_search_key())
            if not ret_list and isinstance(result, (list, tuple)):
                result = result[0] if result else ''
        else:
            result = ExpressionParser().eval(expression, None if absolute else sobject, vars=self.vars,
                                 single=not ret_list, list=ret_list, show_retired=self.show_retired)
        if result is None or result == []:
            return ''
        if isinstance(result, datetime.datetime):
            return SPTDate.convert_to_local(result)
        if ret_list and isinstance(result, (list, tuple)):
            return [str(SPTDate.convert_to_local(value) if isinstance(value, datetime.datetime)
                        else value.get_display_value() if hasattr(value, 'get_display_value') else value)
                    for value in result]
        return result.get_display_value() if hasattr(result, 'get_display_value') else result

    def get_data(self, sobject):
        self.init_kwargs()
        try:
            return self._get_result(sobject, self.expression)
        except Exception:
            return ''

    def get_text_value(self):
        """Native SDK/CSV value: alternate expression, comma join and display format."""
        self.init_kwargs()
        self.sobject = self.get_current_sobject()
        if self.sobject.get_base_search_type() == 'sthpw/virtual' or not (self.expression or self.alt_expression):
            return self.get_value()
        result = self._get_result(self.sobject, self.alt_expression or self.expression)
        if isinstance(result, (list, tuple)):
            result = ','.join(str(value) for value in result)
        if self.get_option('display_format'):
            result = FormatValue().get_format_value(result, self.get_option('display_format'))
        # Source SDK contract stores the value on the in-memory SObject.
        # Vue uses get_cell_value(), which does not modify that object.
        self.sobject.set_value(self.get_name(), result)
        return result

    def get_cell_value(self):
        """Typed equivalent of the source display calculation, without HTML."""
        self.init_kwargs()
        sobject = self.get_current_sobject()
        result = self._get_result(sobject, self.expression) if self.expression else self.get_value()
        if result == '' or result == []:
            return {'text': self.get_option('empty')}
        if self.mode == 'boolean':
            return {'text': str(result), 'checked': bool(result) and result != 'false'}
        if self.mode == 'check':
            try:
                checked = int(result) > 0
            except (ValueError, TypeError):
                checked = False
            return {'text': str(result), 'checked': checked}
        results = result if isinstance(result, (list, tuple)) else [result]
        display_sobject = sobject
        if self.get_option('display_expression'):
            # Legacy display expressions can reference the computed column by name.
            display_sobject = copy(sobject)
            display_sobject.set_data(dict(sobject.get_data(), **{self.get_name(): result}))
            display_sobject.set_update_data({})
        values = []
        for value in results:
            if self.get_option('display_expression'):
                value = Search.eval(self.get_option('display_expression'), display_sobject,
                                    single=self.get_option('return') != 'list',
                                    list=self.get_option('return') == 'list',
                                    vars={'VALUE': str(value)}, show_retired=self.show_retired)
            elif self.get_option('display_format'):
                value = FormatValue().get_format_value(value, self.get_option('display_format'))
            values.append(', '.join(str(item) for item in value) if isinstance(value, (list, tuple)) else str(value))
        return {'text': ', '.join(values)}

    def set_td(self, td):
        self.td = td

    def evaluate_summary(self, sobjects, mode='bottom'):
        self.init_kwargs()
        expression = self.get_option('group_bottom' if mode == 'group_bottom' else 'bottom')
        if not expression:
            return ''
        result = Search.eval(expression, list(sobjects or []), single=True, show_retired=self.show_retired)
        if result in (None, []):
            return ''
        if self.get_option('display_format'):
            result = FormatValue().get_format_value(result, self.get_option('display_format'))
        return str(result)


class ExpressionRecalculateCmd(Command):
    def execute(self):
        from pyasm.widget import WidgetConfigView
        keys = self.kwargs.get('search_keys')
        if not keys:
            return
        objects = Search.get_by_search_keys(keys)
        if not objects:
            return
        name = self.kwargs.get('element_name')
        config = WidgetConfigView.get_by_search_type(objects[0].get_base_search_type(), 'definition')
        widget = config.get_display_widget(name)
        if not isinstance(widget, ExpressionElementWdg):
            raise ValueError('Choose an expression column to recalculate')
        # Recalculation must compute the expression rather than reread stale cache.
        widget.set_option('use_cache', False)
        widget.set_sobjects(objects)
        widget.preprocess()
        for index, obj in enumerate(objects):
            widget.set_current_index(index)
            value = widget.get_text_value()
            obj.set_value(name, value)
            obj.commit()


class ExpressionValueElementWdg(SimpleTableElementWdg):
    ARGS_KEYS = {}

    def get_text_value(self):
        if self.get_current_sobject().is_insert():
            return
        try:
            return Search.eval(self.get_value())
        except Exception:
            return 0

    def get_cell_value(self):
        if self.get_current_sobject().is_insert():
            return {'text': ''}
        value = ExpressionParser().eval(self.get_value(),
                                       env_sobjects={'sobject': self.get_current_sobject()}, use_cache=False)
        return {'text': str(value)}
