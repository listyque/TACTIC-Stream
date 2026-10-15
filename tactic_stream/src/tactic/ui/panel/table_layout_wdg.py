# Copyright (c) 2009, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Native layout configuration entry points; browser rendering belongs to Vue."""
from .base_table_layout_wdg import BaseTableLayoutWdg
from pyasm.web import Table, DivWdg
from pyasm.search import Search
from pyasm.common import Environment
from pyasm.biz import Project
from pyasm.security import Sudo
basestring = str
from pyasm.common.errors import UnsupportedContract


class TableLayoutWdg(BaseTableLayoutWdg):
    def get_display(self):
        """Native column-rendering path; interactive legacy table chrome is separate."""
        # shortcut: only the API cell renderer is ported; migrate the native shell before enabling full HTML tables.
        if not getattr(self, 'render_column_cells', False):
            raise UnsupportedContract('Native HTML table rendering shell is not migrated; get_column_widgets is supported')
        if any(self.kwargs.get(key) for key in ('group_elements', 'group_columns', 'hierarchy', 'expression')):
            raise UnsupportedContract('Native HTML grouping/hierarchy/search expressions are not migrated')
        if self.current_index == -1:
            search = Search(self.search_type)
            search.set_limit(int(self.kwargs.get('limit') or 50))
            self.set_sobjects(search.get_sobjects(), search)
        table = Table()
        self.table = table
        self.mode = 'widget'
        self.view_editable = self.kwargs.get('edit') not in (False, 'false')
        self.num_lock_columns = 0
        self.error_columns = set()
        self.edit_wdgs = {}
        self.attributes = [self.config.get_element_attributes(widget.get_name()) for widget in self.widgets]
        self.color_maps = self.get_color_maps()
        self.kwargs.setdefault('column_widths', [widget.get_width() for widget in self.widgets])
        for widget in self.widgets:
            widget.set_sobjects(self.sobjects, self.search)
            widget.set_parent_wdg(self)
            widget.preprocess()
        for index, sobject in enumerate(self.sobjects):
            row = table.add_row()
            row.add_class('spt_table_row')
            row.add_attr('spt_search_key', sobject.get_search_key())
            # Original data rows begin with the drag and selection cells.
            table.add_cell()
            table.add_cell()
            self.is_insert = sobject.is_insert()
            self.handle_column_cells(table, row, sobject, index)
        return table

    def get_layout_version(self):
        return '2'

    def remap_display_handler(self, display_handler):
        if display_handler in ('HiddenRowToggleWdg', 'pyasm.widget.HiddenRowToggleWdg'):
            return 'tactic.ui.table.HiddenRowElementWdg'

    def handle_column_cells(self, table, tr, sobject, row, level=0):
        lock_width = 0
        parts = self.search_type.split('/')
        collection_type = '%s/%s_in_%s' % (parts[0], parts[1], parts[1])
        for i, widget in enumerate(self.widgets):
            element_name = widget.get_name()
            td = table.add_cell()
            td.add_class("spt_cell_edit")
        
            ### start ########  code to make asset view collection tile clickable ###############
            #this view is always table since "asset_view" is only used in Detail Layout
            view_mode = "table"
        
            collection_key = ""
            collection_code = ""
            collection_path = ""
            collection_parent_path = ""
            isCollection = False
        
            isCollection = sobject.get_value("_is_collection", no_exception=True)
            if (isCollection) and (element_name == "asset_view"):
                collection_parent_path = self.kwargs.get("path")# this needs some work
                collection_path = sobject.get_name()
                if not collection_path:
                    collection_path = self.kwargs.get("collection_path")
        
                collection_code = sobject.get_code()
                self.kwargs["collection_code"] = collection_code
                collection_key = sobject.get_search_key()
                self.kwargs["collection_key"] = collection_key
        
                tr.add_relay_behavior( {
                    'type': 'click',
                    'mode': view_mode,
                    'search_type': self.search_type,
                    'collection_type': collection_type,
                    'collection_key': collection_key,
                    'collection_code': collection_code,
                    'collection_path': collection_path,
                    'collection_parent_path': collection_parent_path,
                    'bvr_match_class': 'spt_thumb_top',
                    'cbjs_action': r'''
                    var top = bvr.src_el.getParent(".spt_collection_top");
                    var content = top.getElement(".spt_collection_content");
                    var layout = bvr.src_el.getParent(".spt_layout");
                    spt.table.set_layout(layout);
        
                    var collection_key = bvr.src_el.getAttribute("spt_collection_key");
                    if (!collection_key) {
                        collection_key = bvr.collection_key;
                        content.setAttribute("spt_collection_key", collection_key);
                    }
                    var collection_code = bvr.src_el.getAttribute("spt_collection_code");
                    if (!collection_code) {
                       collection_code = bvr.collection_code;
                       content.setAttribute("spt_collection_code", collection_code);
                    }
        
                    var collection_path = bvr.collection_path;
        
                    //build collection path
                    //this needs some work in the future
                    //steps in path are missed in some circumstances
                    //i.e. when in a sub collection in detail layout then changing the view to collection layout does not pass the path correctly
                    var path = "";
                    if (!bvr.collection_parent_path && !collection_path) {
                        path = "/";
                    }
                    else if (!bvr.collection_parent_path && collection_path) {
                        path = collection_path;
                    }
                    else {
                        path = bvr.collection_parent_path+"/"+collection_path;
                    }
                    content.setAttribute("spt_collection_path", path);
        
                    var expr = "@SEARCH("+bvr.collection_type+"['parent_code','"+collection_code+"']."+bvr.search_type+")";
        
                    var parent_dict = {};
                    var parent_collection = bvr.src_el.getParent(".spt_subcollection_wdg");
        
                    if (parent_collection) {
                        for (var i = 0; i < collection_path.split("/").length - 1; i++) {
                            var n = path.lastIndexOf("/");
                            var collection_name = path.substring(n+1);
                            path = path.substring(0, n);
                            var parent_key = parent_collection.getAttribute("spt_parent_key");
                            parent_dict[collection_name] = parent_key;
                            parent_collection = parent_collection.getParent(".spt_subcollection_wdg");
                        }
                    }
        
                    var class_name = "tactic.ui.panel.CollectionContentWdg";
                    var element_names = bvr.src_el.getParent(".spt_element_names");
                    var kwargs = {
                        collection_key: collection_key,
                        path: path,
                        search_type: bvr.search_type,
                        show_shelf: false,
                        show_search_limit: true,
                        expression: expr,
                        parent_dict: parent_dict,
                        element_names: element_names,
                        mode: bvr.mode,
                    }
                    spt.panel.load(content, class_name, kwargs);
                    '''
                })
        
                ### end ########   code to make asset view collection tile clickable ###############
        
            if sobject.is_insert():
                onload_js = widget.get_onload_js()
                if onload_js:
                    td.add_behavior( {
                        'type': 'load',
                        'cbjs_action': '''
                        try {
                            bvr.src_el.loadXYZ = function(element_name,cell, sobject) { %s }
                        }
                        catch(e) {
                            console.log("Error in load code for column");
                        }
                        ''' % onload_js
                    } )
        
        
        
            widths = self.kwargs.get("column_widths")
            if widths and widths[i] != -1:
                td.add_style("width", widths[i])
                td.add_attr("last_width", widths[i])
            else:
                td.add_style("width", "auto")
                td.add_attr("last_width", widths[i])
        
        
            # TEST
            if i < self.num_lock_columns:
                td.add_style("position: absolute")
                td.add_style("background: inherit")
                td.add_style("background-color: inherit")
        
        
                if i == self.num_lock_columns-1:
                    td.add_style("border-right: solid 2px #CCC")
                    #td.add_style("border-left: none")
        
                td.add_style("left: %spx" % lock_width)
                td.add_attr("spt_lock_width", lock_width)
                td.add_style("z-index: 10")
                td.add_class("spt_table_cell_fixed")
        
        
                self.expand_on_load = False
        
        
        
                # NOTE: widths must obviously exist, but there is a check before to see if it does
        
                cur_width = widths[0]
                if isinstance(cur_width, basestring):
                    cur_width = int(cur_width.replace("px",""))
                lock_width += cur_width
        
        
        
        
                if sobject.is_insert():
                    load_div = DivWdg()
                    self.top.add(load_div)
        
                    load_div.add_behavior( {
                        'type': 'load',
                        'lock_columns': self.num_lock_columns,
                        'cbjs_action': '''
                        var el = bvr.src_el;
                        if (el.processed == true) return;
        
                        el.processed = true;
        
                        var lock_columns = bvr.lock_columns;
        
                        var top = bvr.src_el.getParent(".spt_layout_top");
                        var layout = top.getElement(".spt_layout");
                        spt.table.set_layout(layout);
                        spt.table.expand_table("free");
        
                        var table = spt.table.get_table();
                        var header_table = layout.getElement(".spt_table_with_headers");
                        var table_scroll = layout.getElement(".spt_table_scroll");
        
                        table_scroll.setStyle("position", "relative");
        
        
                        // removed fixed layout for now
                        table.setStyle("table-layout", "fixed")
                        header_table.setStyle("table-layout", "fixed")
        
        
                        var table_els = table.getElements(".spt_table_cell_fixed");
                        table_els.forEach( function(el) {
                            el.setStyle("position", "absolute");
                            el.setStyle("background", "inherit");
                        } );
        
                        header_table.setStyle("width", "max-content");
                        table.setStyle("width", "max-content");
        
                        // sync all of the row heights
        
                        var resize_heights = function() {
        
                            if (!layout.isVisible()) return;
                            spt.table.set_layout(layout);
        
                            var rows = spt.table.get_all_rows();
                            for (var i = 0; i < rows.length; i++) {
        
                                var height = rows[i].getSize().y;
        
                                var table_els = rows[i].getElements(".spt_table_cell_fixed");
                                for (var j = 0; j < table_els.length; j++) {
                                    if (table_els[j].scrollHeight > height) {
                                        height = table_els[j].scrollHeight;
                                    }
                                }
                                for (var j = 0; j < table_els.length; j++) {
                                    table_els[j].setStyle("height", height);
                                }
                                rows[i].setStyle("height", height);
                            }
                        }
                        resize_heights();
        
                        var interval_id = setInterval( function(e) {
                            resize_heights()
                        }, 1000);
                        bvr.src_el.height_interval_id = interval_id;
        
        
        
                        var header_els = header_table.getElements(".spt_table_cell_fixed");
                        header_els.forEach( function(el) {
                            el.setStyle("position", "absolute");
                            //var height = "35px";
                            //el.setStyle("height", height);
        
                        } );
        
        
        
                        var offset = 120*lock_columns;
                        header_table.setStyle("margin-left", offset);
                        table.setStyle("margin-left", offset);
        
        
        
                        var scroll = document.id(document.createElement("div"));
                        scroll.addClass("spt_horizontal_scroll");
                        scroll.inject(table_scroll, "after");
                        var scroll_content = document.id(document.createElement("div"));
                        scroll_content.inject(scroll);
                        scroll_content.innerHTML = "hello";
        
                        scroll.setStyle("position", "relative");
                        scroll.setStyle("width", "100%");
                        scroll.setStyle("background", "blue");
                        scroll.setStyle("height", "17px");
                        //scroll.setStyle("margin-top", "-17px");
                        scroll.setStyle("overflow-x", "scroll");
                        scroll.setStyle("overflow-y", "hidden");
        
                        scroll.setStyle("z-index", "2");
                        table_scroll.setStyle("z-index", "1");
        
                        setTimeout( function() {
                            var size = table_scroll.getSize().x;
                            scroll.setStyle("width", size);
        
                            var size2 = table_scroll.scrollWidth;
                            var size2 = header_table.getSize().x;
                            scroll_content.setStyle("width", size2+offset+100);
        
                            if (size2 <= size) {
                                //scroll.setStyle("display", "none");
                            }
        
                        }, 1000);
        
                        // remove the scrollbars
                        table_scroll.setStyle("overflow-x", "hidden");
        
                        //scroll.setStyle("border", "solid 2px green");
                        //scroll.scrollLeft = 30;
                        scroll.onscroll = function(e) {
                            header_table.setStyle("margin-left", -scroll.scrollLeft+offset);
                            table.setStyle("margin-left", -scroll.scrollLeft+offset);
                        }
        
        
                        // add an observer to the layout
                        /*
                        var callback = function() {
                            var size = header_table.getSize();
                            scroll_content.setStyle("width", size.x+120);
                            //var size = layout.getSize();
                            //scroll.setStyle("width", size.x);
                        }
                        var observer = new ResizeObserver(callback);
                        observer.observe(header_table);
                        layout.setStyle("border", "solid 1px red");
                        */
        
        
                        '''
                    } )
        
                    load_div.add_behavior( {
                        'type': 'unload',
                        'lock_columns': self.num_lock_columns,
                        'cbjs_action': '''
                        var interval_id = bvr.src_el.height_interval_id = interval_id;
                        clearTimeout(interval_id);
                        '''
                    } )
        
            # Qt webkit ignores these
            #if self.browser == 'Qt':
            #    td.add_style("background-repeat: no-repeat")
            #    td.add_style("background-position: bottom right")
            #    td.add_style("vertical-align: top")
        
            # add spacing
            if level and element_name == self.level_name:
                td.add_style("padding-left: %spx" % (level*self.level_spacing))
        
            if self.mode == 'widget':
                widget.set_current_index(row)
        
                try:
                    if element_name in self.error_columns:
                        td.add(IconWdg("Error Found: see above", IconWdg.WARNING, True) )
                    else:
                        html = widget.get_buffer_display()
                        if not html:
                            html = "<div style='height: 14px'>&nbsp;</div>"
                        td.add(html)
                except Exception:
                    raise
        
            else:
                value = sobject.get_value(element_name, no_exception=True)
                td.add(value)
        
        
            self.name = widget.get_name()
            self.value = sobject.get_value(element_name, no_exception=True)
        
            if not self.is_insert and self.mode == 'widget':
                self.handle_color(td, widget, i)
        
                # provide an opportunity for the widget to affect the td and tr
                widget.handle_tr(tr)
                widget.handle_td(td)
            elif self.is_insert:
                widget.handle_tr(tr)
                widget.handle_td(td)
        
            is_editable = True
            # Check if view is editable first, if not, skip checking each column
            if self.view_editable:
                if not widget.is_editable():
                    is_editable = False
                else:
                    security = Environment.get_security()
                    if not security.check_access('element', {'name': element_name}, "edit", default='edit'):
                        is_editable = False
        
        
            # This is only neccesary if the table is editable
            if self.view_editable:
        
                edit = self.edit_wdgs.get(element_name)
        
                # insert rows have no edits defined yet
                if self.is_insert:
                    if not is_editable:
                        td.add_class("spt_cell_insert_no_edit")
        
                elif not edit or not is_editable:
                    td.add_class("spt_cell_no_edit")
        
        
                #get the value from the widget, else use self.value
                if edit:
                    edit.set_sobject(sobject)
                    values = edit.get_values()
                    column = edit.get_column()
                    value = values.get('main')
                    if not value and value != False:
                        value = ''
                else:
                    value = self.value
        
                ## add timezone conversion
                ##if not SObject.is_day_column(element_name):
                ##    element_type = SearchType.get_tactic_type(self.search_type, element_name)
        
                ##    if element_type in ['time', 'datetime']:
                ##        value = widget.get_timezone_value(value)
        
                if isinstance(value, basestring):
                    value = value.replace('"', '&quot;')
        
        
                elif isinstance(value, bool):
                    value = str(value).lower()
        
                elif isinstance(value, dict) or isinstance(value, list):
                    import json
                    value = json.dumps(value, indent=2, sort_keys=True)
                    value = value.replace('"', "&quot;")
        
        
                if value == None:
                    value = ""
        
                if td.get_attr("spt_input_value") == None:
                    td.add_attr("spt_input_value", value)
                #td.add_attr("spt_input_column", column)
            else:
                td.add_class("spt_cell_no_edit")
        
        
        
            # if this is an insert, then set the element name
            if self.is_insert:
                td.add_attr("spt_element_name", element_name)

    def get_color_maps(self):
    
            # get the color maps
            from pyasm.widget import WidgetConfigView
            color_config = WidgetConfigView.get_by_search_type(self.search_type, "color")
            color_xml = color_config.configs[0].xml
            self.color_maps = {}
            for widget in self.widgets:
                name = widget.get_name()
                xpath = "config/color/element[@name='%s']/colors" % name
                text_xpath = "config/color/element[@name='%s']/text_colors" % name
                bg_color_node = color_xml.get_node(xpath)
                bg_color_map = color_xml.get_node_values_of_children(bg_color_node)
    
                text_color_node = color_xml.get_node(text_xpath)
                text_color_map = color_xml.get_node_values_of_children(text_color_node)
    
                # use old weird query language
                query = bg_color_map.get("query")
                query2 = bg_color_map.get("query2")
                if query:
                    bg_color_map = {}
    
                    search_type, match_col, color_col = query.split("|")
                    try:
                        sudo = Sudo()
                        search = Search(search_type)
                        sobjects = search.get_sobjects()
                    finally:
                        sudo.exit()
    
                    # match to a second atble
                    if query2:
                        search_type2, match_col2, color_col2 = query2.split("|")
                        search2 = Search(search_type2)
                        sobjects2 = search2.get_sobjects()
                    else:
                        sobjects2 = []
    
                    for sobject in sobjects:
                        match = sobject.get_value(match_col)
                        color_id = sobject.get_value(color_col)
    
                        for sobject2 in sobjects2:
                            if sobject2.get_value(match_col2) == color_id:
                                color = sobject2.get_value(color_col2)
                                break
                        else:
                            color = color_id
    
    
                        bg_color_map[match] = color
    
                self.color_maps[name] = bg_color_map, text_color_map
            return self.color_maps

    def handle_color(self, td, widget, index):
    
            # add a color based on the color map if color is not set to false
            disable_color = self.attributes[index].get("color") == 'false'
            if disable_color:
                return
    
            bg_color = None
            text_color = None
    
            if self.name is None:
                name = widget.get_name()
            else:
                name = self.name
    
            try:
                if self.value is None:
                    value = widget.get_value()
                else:
                    value = self.value
    
                if not isinstance(value, basestring):
                    value = str(value)
                bg_color_map, text_color_map = self.color_maps.get(name)
                if bg_color_map:
                    bg_color = bg_color_map.get(value)
                    if bg_color:
                        td.add_style("background-color", bg_color)
                if text_color_map:
                    text_color = text_color_map.get(value)
                    if text_color:
                        td.add_style("color", text_color)
            except Exception as e:
                print('WARNING: problem when getting widget value for color mapping on widget [%s]: ' % widget, "message=[%s]" % str(e))


class FastTableLayoutWdg(TableLayoutWdg):
    pass

