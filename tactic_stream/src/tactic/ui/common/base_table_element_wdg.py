# Copyright (c) 2005-2009, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Native column metadata and values from base_table_element_wdg.py."""
from pyasm.widget.table_element_wdg import BaseTableElementWdg as FormerBaseTableElementWdg
from pyasm.web import DivWdg, Widget, WikiUtil
from pyasm.search import Search, SearchType, SObject
from dateutil import parser
import locale
basestring = str


class BaseTableElementWdg(FormerBaseTableElementWdg):
    @classmethod
    def is_editable(cls):
        return True

    def is_sortable(self):
        return bool(self.get_option('order_by'))

    def is_groupable(self):
        return bool(self.get_option('order_by'))

    def get_sort_prefix(self):
        return None

    def alter_order_by(self, search, direction=''):
        search.add_order_by(self.get_option('order_by') or self.get_name(), direction)
        order_by_where = self.get_option('order_by_where')
        if order_by_where:
            search.add_where(order_by_where)

    def _add_css_style(self, element, prefix, name=None, value=None):
            # skip the edit/ insert row
            #sobject = self.get_current_sobject()
            #if not sobject or sobject.get_id() == -1:
            #    return
    
            if value is None:
                value = self.get_value()
            if name is None:
                name = self.get_name()
    
            if not value:
                value = 0
            
            vars = {
                "ELEMENT":  name,
                "VALUE":    value
            }
    
    
            for key, expr in self.kwargs.items():
                if not key.startswith("%s" % prefix):
                    continue
    
                if expr:
                    sobject = self.get_current_sobject()
                    prefix, property = key.split("_", 1)
                    value = Search.eval(expr, sobject, vars=vars)
                    if value:
                        element.add_style("%s: %s" % (property, value) )

    def handle_td(self, td):
            name = self.name
            value = self.value
            self._add_css_style(td, 'css_', name, value)

    def handle_tr(self, tr):
            name = self.name
            value = self.value
            self._add_css_style(tr, 'rowcss_', name, value)


class RawTableElementWdg(BaseTableElementWdg):
    def is_sortable(self):
        return True

    def get_required_columns(self):
        return [self.get_name()]


class SimpleTableElementWdg(BaseTableElementWdg):
    def is_sortable(self):
        return True

    def get_required_columns(self):
        return [self.get_name()]

    def is_groupable(self):
        return True

    def is_time_groupable(self):
        return False


    def add_value_update(self, value_wdg, sobject, name):
            value_wdg.add_update( {
                'search_key': sobject.get_search_key(),
                'column': name,
                'interval': 4,
            } )

    def get_display(self):
            sobject = self.get_current_sobject()
    
            column =  self.kwargs.get('column')
            if column:
                name = column
            else:
                name = self.get_name()
            
            value = self.get_value(name=name)
    
            empty = self.get_option("empty")
            if empty and self.is_editable() and not value:
                from pyasm.web import SpanWdg
                div = DivWdg()
                div.add_style("text-align: center")
                div.add_style("width: 100%")
                div.add_style("white-space: nowrap" )
                if empty in [True, 'true']:
                    div.add("--Select--")
                div.add_style("opacity: 0.5")
                return div
    
    
    
    
            if sobject:
                data_type = SearchType.get_column_type(sobject.get_search_type(), name)
            else:
                data_type = 'text'
    
            if isinstance(value, basestring):
                wiki = WikiUtil()
                value = wiki.convert(value) 
            if name == 'id' and value == -1:
                value = ''
            elif data_type in ["timestamp","time"] or name == "timestamp":
                if value == 'now':
                    value = ''
                elif value:
                    # This date is assumed to be GMT
                    date = parser.parse(value)
                    # convert to user timezone
                    if not SObject.is_day_column(name):
                        date = self.get_timezone_value(date)
                    try:
                        encoding = locale.getlocale()[1]		
                        value = date.strftime("%b %d, %Y - %H:%M").decode(encoding)
                    except:
                        value = date.strftime("%b %d, %Y - %H:%M")
    
                else:
                    value = ''
            elif isinstance(value, dict) and not value:
                value = ""
            elif value is None:
                value = ""
            else:
                if isinstance(value, Widget):
                    return value
                elif not isinstance(value, basestring):
                    try:
                        value + 1
                    except TypeError:
                        value = str(value)
                    #else:
                    #    value_wdg.add_style("float: right")
                    #    value_wdg.add_style("padding-right: 3px")
    
    
            min_height = self.get_option("min_height")
            single_line = self.get_option("single_line") or False
    
            value_wdg = DivWdg()
            if single_line in ["true", True]:
                value_wdg.add_style("line-height: %spx" % min_height)
                value_wdg.add_style("white-space: nowrap")
                value_wdg.add_style("overflow-y: hidden")
    
            value_wdg.add_style("overflow-x: hidden")
            value_wdg.add_style("text-overflow: ellipsis")
    
    
            # some properties
            if min_height:
                value_wdg.add_style("min-height: %spx" % min_height)
    
            if sobject and SearchType.column_exists(sobject.get_search_type(), name):
    
                self.add_value_update(value_wdg, sobject, name)
    
                # don't call str() to prevent utf-8 encode error
                value_wdg.add(value)
    
    
    
                link_expression = self.get_option("link_expression")
                if link_expression:
                    value_wdg.add_class("tactic_new_tab")
                    value_wdg.add_style("display: inline-block")
                    value_wdg.add_attr("search_key", sobject.get_search_key())
                    value_wdg.add_style("text-decoration: underline")
                    #value_wdg.add_attr("spt_class_name", "tactic.ui.tools.SObjectDetailWdg")
                    value_wdg.add_class("hand")
    
            else:
                value_wdg.add(value)
    
    
            # TEST: loading values dynamically using javascript
            """
            value_wdg.add_attr("spt_value", value)
            value_wdg.add_attr("spt_name", name)
            value_wdg.add_class("spt_update_cellX")
            value_wdg.add_behavior( {
                'type': 'load',
                'cbjs_action': '''
                bvr.src_el.update = function(data) {
                    var el = document.id(this);
                    var name = el.getAttribute("spt_name");
                    var value = data[name];
                    el.innerHTML = value + "!!!";
    
                }
    
                var name = bvr.src_el.getAttribute("spt_name");
                var value = bvr.src_el.getAttribute("spt_value");
                var data = {};
                data[name] = value;
                bvr.src_el.update( data );
                '''
            } )
            """
    
    
            return value_wdg
