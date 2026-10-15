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


__all__ = ['FormatElementWdg']

import re, datetime

from pyasm.common import TimeCode
from pyasm.search import SObject, Search, SearchKey, SearchType
from pyasm.web import DivWdg, WebContainer, SpanWdg, Widget
from pyasm.biz import Schema, Project, ProdSetting, PrefSetting
from pyasm.widget import HiddenWdg, IconWdg

from tactic.ui.common import SimpleTableElementWdg

from dateutil import parser

from tactic.core.format_value import FormatValueMixin

class FormatElementWdg(FormatValueMixin, SimpleTableElementWdg):

    ARGS_KEYS = {
    'type': {
        'description': 'Determines the type it should be displayed as',
        #'type': 'SelectWdg',
        'type': 'tactic.ui.manager.FormatDefinitionEditWdg',
        'values': 'integer|float|percent|currency|date|time|scientific|boolean|text|timecode',
        'category': 'Required',
        'default': 'text',
        'order': 1
    },
    'total_summary': {
        'description': 'Determines a calculation for the bottom row',
        'type': 'SelectWdg',
        'values': 'count|total|average',
        'category': 'Misc',
        'order': 2
    },
    'format': {
        'description': 'display format',
        'category': 'internal',
        'sub_keys': ['fps']
    },

    'constraint': {
        'description': 'Determines what kind of index is put onto the created column',
        'type': 'SelectWdg',
        'values': 'unique|indexed',
        'order': 3,
        'category': 'Misc',
    }

    }


    def handle_layout_behaviors(self, layout):
        layout.add_relay_behavior( {
        'type': 'mouseup',
        #'propagate_evt': True, # not sure if this works
        'bvr_match_class': 'spt_format_checkbox_%s' % self.get_name(),
        'cbjs_action': '''
        var layout = bvr.src_el.getParent(".spt_layout");
        var version = layout.getAttribute("spt_version");
        if (version == "2") {
            var value_wdg = bvr.src_el;
            var checkbox = value_wdg.getElement(".spt_input");
            // FIXME: Not sure why we have to replicate checkbox basic behavior ...
            if (checkbox.checked) {
                checkbox.checked = false;
            }
            else{
                checkbox.checked = true;
            }

            spt.table.set_layout(layout);
            spt.table.accept_edit(checkbox, checkbox.checked, false)

        }
        else {
            var cached_data = {};
            var value_wdg = bvr.src_el;
            var top_el = bvr.src_el.getParent(".spt_boolean_top");
            spt.dg_table.edit.widget = top_el;
            var key_code = spt.kbd.special_keys_map.ENTER;
            spt.dg_table.inline_edit_cell_cbk( value_wdg, cached_data );
        }
        '''
        } )


    def get_width(self):
        widget_type = self.get_option("type")
        if widget_type in ['integer']:
            return 30
        elif widget_type in ['float', 'date', 'timecode', 'currency']:
            return 80
        else:
            return 100



    def get_display(self):

        top = DivWdg()

        value = self.get_value()
        widget_type = self.get_option("type")
        

        justify = self.get_option('justify')
        if justify:
            self.justify = justify
        else:
            self.justify = None



        if widget_type in ['integer', 'float', 'timecode', 'currency']:
            if not self.justify:
                top.add_style("float: right")
                self.justify = "right"

        elif widget_type in ['date','time']:
            name = self.get_name()
            if value and not SObject.is_day_column(name):               

                try:
                    value = self.get_timezone_value(value)
                except:
                    pass
         
                value = str(value)

        else:
            if not self.justify:
                top.add_style("float: left")
                self.justify = "left"

        top.add_style("padding-right: 3px")

        top.add_style("min-height: 15px")

        format = self.get_option('format')
        try:
            value = self.get_format_value( value, format )
        except Exception as e:
            value = "Bad Date [%s]" % value
            
        top.add(value)


        sobject = self.get_current_sobject()
        if sobject:

            column =  self.kwargs.get('column')
            if column:
                name = column
            else:
                name = self.get_name()

            top.add_update( {
                'search_key': sobject.get_search_key(),
                'column': name,
                'format': format

            } )

        return top

    def get_text_value(self):

        value = self.get_value()
        widget_type = self.get_option("type")
        
        if widget_type in ['date','time'] and value:
            name = self.get_name()
            if not SObject.is_day_column(name):
                value = self.get_timezone_value(value)
                value = str(value)
 
        format = self.get_option('format')
        
        if format == 'Checkbox':
            value = str(value)
        else:
            value = self.get_format_value( value, format )

       
        return value

    def get_bottom_wdg(self):
        # check if the user has enabled it
        info = self.check_bottom_wdg()

        if info.get('check') == False:
            return None

        
        title = info.get('title')
        result = info.get('result')
        format = self.get_option('format')
        result = self.get_format_value( result, format )

        div = DivWdg()
        div.add(title)
        div.add(str(result))
        div.add_style("text-align: right")
        div.add_class( "spt_%s_expr_bottom" % (self.get_name()) )
        return div



    def get_group_bottom_wdg(self, sobjects):

        summary = self.get_option("total_summary")
        if not summary:
            return None

        # parse the expression
        self.vars = self.get_vars()
 
        expression, title = self.get_expression(summary)
        try:
            result = Search.eval(expression, sobjects=sobjects, vars=self.vars)
        except Exception as e:
            print("WARNING: ", e.message)
            result = "Calculation Error"
            title = ''
        """
        widget_type = self.get_option("type")
        
        if widget_type in ['date','time']:
            name = self.get_name()
            if not SObject.is_day_column(name):
                result = SPTDate.convert_to_local(result)
                result= str(result)
        """
        format = self.get_option('format')
        formatted_result = self.get_format_value( result, format )

        div = DivWdg()
        div.add(str(formatted_result))
        div.add_style("text-align: right")

        return div, result







   



    def format_checkbox(self, value):
        div = DivWdg()
        div.add_class("spt_boolean_top")
        from pyasm.widget import CheckboxWdg
        checkbox = CheckboxWdg(self.get_name())
        if self.attributes.get('edit') == 'false':
            checkbox.set_option('disabled','disabled')


        checkbox.set_option("value", "true")
        if value:
            checkbox.set_checked()
        else:
            checkbox.set_unchecked()
        div.add(checkbox)
        checkbox.add_style("pointer-events", "none")

        div.add_class('spt_format_checkbox_%s' % self.get_name())

        div.add_behavior( {
        'type': 'click',
        'cbjs_action': '''

        var cached_data = {};

        //var top_el = bvr.src_el.getParent(".spt_boolean_top");
        // var value_wdg == bvr.src_el;
        var top_el = bvr.src_el;
        var value_wdg = bvr.src_el.getElement("input");

        spt.dg_table.edit.widget = top_el;
        var key_code = spt.kbd.special_keys_map.ENTER;
        spt.dg_table.inline_edit_cell_cbk( value_wdg, cached_data );



        var cell = bvr.src_el.getParent(".spt_edit_cell");
        if (cell) {
            if (cell.getAttribute("spt_input_value") == "false") {
                cell.setAttribute("spt_input_value", "true");
                value_wdg.checked = true;
            }
            else {
                cell.setAttribute("spt_input_value", "false");
                value_wdg.checked = false;
            }
        }

        //bvr.src_el.checked = !bvr.src_el.checked;
        //value_wdg.checked = !value_wdg.checked;

        '''
        } )

        return div

    def format_negative_currency(self, value):
        return "<span style='color: #F00'>(%s)</span>" % value

    def handle_th(self, th, index):
        format = self.get_option('format')
        if format == 'Checkbox':
            th.add_attr("spt_input_type", "inline")
            #th.add_style("text-align: center")

        self.add_simple_search(th)

    def handle_td(self, td):
        super(FormatElementWdg, self).handle_td(td)
        #version = self.parent_wdg.get_layout_version()
        #if version == "2":
        #    return
        format = self.get_option('format')
        if format == 'Checkbox':
            td.add_attr("spt_input_type", "inline")
            td.add_style("text-align: center")

        if self.justify:
            td.add_style("text-align: %s" % self.justify)
        
 




