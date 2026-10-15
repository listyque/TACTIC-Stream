"""Original GeneralFilterWdg's server-side column filter engine.

Moved verbatim from src/tactic/ui/filter/filter_wdg.py in the supplied 5.0
source (except self-class references). Rendering stays in GeneralFilterWdg.
Callers of this legacy engine MUST validate untrusted values; some old relations
use raw SQL or the trusted server expression language. Native inputs are
validated by query_model.py before calling this engine.
"""
# Copyright (c) 2005 Southpaw Technology. Distributed under repository LICENSE.
import re
from pyasm.common import Date, TimeCode
from pyasm.search import Search, SearchType, SearchInputException
from tactic.core.filter_data import FilterData

class OriginalColumnFilter:
    def _add_time_filter(cls, search, column, value, op):
        '''internal method for time related filtering'''

        from dateutil import parser
        try:
            if re.search('day|week|hour|month',value, flags=re.IGNORECASE):
                is_date = False
            else:
                parser.parse(value)
                is_date = True
        except:
            is_date = False

        #import re
        #p = re.compile("\d+-\d+-\d")
        #if re.match(p, value):
        if is_date:
            search.add_where("\"%s\" %s '%s'" % (column, op, value) )
        elif value == 'xxx':
            from dateutil.relativedelta import relativedelta
            from datetime import datetime
            import calendar

            today = datetime.today()
            vars = {
            'MONDAY': today + relativedelta(weekday=calendar.MONDAY),
            'TUESDAY': today + relativedelta(weekday=calendar.TUESDAY),
            'WEDNESDAY': today + relativedelta(weekday=calendar.WEDNESDAY),
            'THURSDAY': today + relativedelta(weekday=calendar.THURSDAY),
            'FRIDAY': today + relativedelta(weekday=calendar.FRIDAY),
            'SATURDAY': today + relativedelta(weekday=calendar.SATURDAY),
            'SUNDAY': today + relativedelta(weekday=calendar.SUNDAY)
            }
            value = Search.eval(value, vars=vars, single=True)
            search.add_filter(column, value, op=op)

        elif ' ' in value:
            num, type = value.split(" ", 1)
            num = int(num)
            now = search.get_database_impl().get_timestamp_now(num,type,op='-')
            search.add_filter(column, now, op=op, quoted=False)
        else:
            raise SearchInputException('Invalid value [%s] is entered. Click on the link again. '%value)

    _add_time_filter = classmethod(_add_time_filter)



    def _evaluate_value(cls, value):
        value = Search.eval(value, single=True)
        return value
    _evaluate_value = classmethod(_evaluate_value)

    def alter_sobject_search(cls, search, values_list, prefix, use_ops=True, mode='sobject'):
        '''alter directly the sobject search
            @mode: sobject|child|parent'''

        num_enabled = 0

        search_type_obj = search.get_search_type_obj()
        base_search_type = search.get_base_search_type()
        search_type = search.get_full_search_type()

        # get the operations

        filter_data = FilterData.get()
        search_ops = filter_data.get_values_by_prefix("search_ops")

        # get the filter mode (if it is used)
        filter_mode = filter_data.get_values_by_prefix("filter_mode")
        if filter_mode:
            filter_mode = filter_mode[0].get("filter_mode")
        else:
            filter_mode = 'and'

        # find out which values list is enabled for compound search
        values_list_enabled = []
        valid_values_list = []
        if use_ops and filter_mode == 'custom':
            for i, values in enumerate(values_list):
                # filter out provided search_type if it exists in values_list
                item_search_type = values.get("%s_search_type" % prefix)

                if item_search_type and base_search_type != item_search_type:
                    continue

                enabled = values.get("%s_enabled" % prefix)
                column = values.get("%s_column" % prefix)
                relation = values.get("%s_relation" % prefix)

                # text box takes precedence
                value = values.get("%s_value" % prefix)
                if not value:
                    value = values.get("%s_select" % prefix)

                # curly braces
                if value and value.startswith("{") and value.endswith("}"):
                    value = cls._evaluate_value(value)

                column_type = SearchType.get_tactic_type(search_type, column)


                # check if this filter is enabled
                if enabled == None:
                    # by default, the filter is enabled
                    is_enabled = True
                else:
                    is_enabled = (str(enabled) in ['on','true'])

                if is_enabled and relation in ['is empty', 'is not empty', 'is distinct']:
                    is_enabled = True
                elif not value or not column or not relation:
                    is_enabled = False

                values_list_enabled.append(is_enabled)
                if is_enabled:
                    valid_values_list.append(values)

        if valid_values_list:
            values_list = valid_values_list

        level_0_count = 0
        if use_ops and search_ops and values_list_enabled:
            levels = []
            ops = []
            search_ops = search_ops[0]
            all_levels = search_ops.get("levels")
            all_ops = search_ops.get("ops")
            all_modes = search_ops.get("modes")


            # filter down to those ops applicable for Filter subsection
            look_ahead = False

            filtered_levels = []
            filtered_ops = []
            filtered_modes = []

            # filter for the applicable levels and ops according to mode
            for op_mode, op_level, op_op in zip(all_modes, all_levels, all_ops):
                if op_mode != mode:
                    continue
                filtered_levels.append(op_level)
                filtered_ops.append(op_op)
                filtered_modes.append(op_mode)


            for idx, (op_mode, op_level, op_op) in enumerate(zip(filtered_modes, filtered_levels, filtered_ops)):
                if idx + 1 > len(values_list_enabled):
                    continue
                # the level 0 after a disabled filter is ignored
                if op_level == 0 and idx + 1 < len(values_list_enabled):
                    if values_list_enabled[idx] == True or values_list_enabled[idx+1] ==True:
                        level_0_count += 1

                    if values_list_enabled[idx] == False and look_ahead==False:
                        continue
                    # look ahead to disable if applicable
                    if values_list_enabled[idx+1] ==False:
                        look_ahead = True
                        continue


                if idx + 1 >= len(values_list_enabled):
                    continue

                # reset level 0 count when it reaches level 1
                if op_level == 1:
                    if values_list_enabled[idx] == True:
                        level_0_count += 1
                    look_ahead = False
                    # if preceding level 0s are all False, skip
                    if level_0_count == 0:
                        continue
                    level_0_count =0
                    if values_list_enabled[idx+1] == True:
                        level_0_count += 1


                levels.append(op_level)
                ops.append(op_op)


        else:
            levels = None
            ops = None

        # discard the trailing dangling level 1 op
        if levels and levels[-1] == 1 and level_0_count == 0:
            levels.pop()
            ops.pop()



        begin_idx = len(search.get_select().get_wheres())
        upper_begin_idx = begin_idx
        for i, values in enumerate(values_list):

            # filter out provided search_type if it exists in values_list
            item_search_type = values.get("%s_search_type" % prefix)
            if item_search_type and base_search_type != item_search_type:
                continue

            enabled = values.get("%s_enabled" % prefix)
            column = values.get("%s_column" % prefix)
            json_key = values.get("%s_key" % prefix)

            relation = values.get("%s_relation" % prefix)
            if enabled and column:
                num_enabled += 1

            # text box takes precedence
            value = values.get("%s_value" % prefix)
            if not value:
                value = values.get("%s_select" % prefix)

            # curly braces
            if value and value.startswith("{") and value.endswith("}"):
                value = cls._evaluate_value(value)

            #column_type = search_type_obj.get_tactic_type(column)
            column_type = SearchType.get_tactic_type(search_type, column)


            # check if this filter is enabled
            if enabled == None:
                # by default, the filter is enabled
                is_enabled = True
            else:
                is_enabled = (str(enabled) in ['on','true'])
            if not is_enabled:
                continue

            special_relation = False
            # handle all of the types
            if relation == "is empty":
                if column_type in ['boolean','integer','float','currency','time','timestamp','datetime2', 'uniqueidentifier']:
                    search.add_filter(column, None)
                else:
                    search.add_where("(\"%s\" = '' or \"%s\" is NULL)" % (column, column) )
                special_relation = True

            elif relation == "is not empty":
                if column_type in ['boolean','integer','float','currency','time','timestamp','datetime2']:
                    search.add_where("(\"%s\" is not NULL)" % column )
                else:
                    search.add_where("(\"%s\" != '' and \"%s\" is not NULL)" % (column, column) )
                special_relation = True

            elif relation == "is distinct":
                #search.set_distinct_col(column)
                #search.add_group_aggregate_filter(column, "id", 'min')
                if column.find('|') != -1:
                    column = column.split('|')
                search.add_distinct_filter(column)
                special_relation = True

            # this must be old
            user = values.get("%s_user" % prefix)
            if user:
                search.add_user_filter()
                continue

            # if the column is json: data->key
            if column_type == "json":
                if json_key:
                    column = "%s->%s" % (column, json_key)


            if not value or not column or not relation or special_relation:
                begin_idx = OriginalColumnFilter.add_ops(search, values_list,  levels, ops, i, begin_idx)
                continue

            if relation == "is":
                search.add_filter(column, value)


            elif relation == "is not":
                search.add_op('begin')
                search.add_filter(column, value, op='!=')
                search.add_filter(column, None)
                search.add_op('or')

            elif relation == "contains":
                search.add_regex_filter(column, value, op="EQI")
            elif relation == "does not contain":
                search.add_op('begin')
                search.add_regex_filter(column, value, op="NEQI")
                search.add_filter(column, None)
                search.add_op('or')

            elif relation == "starts with":
                search.add_filter(column, "%s%%" % value, op="like")
            elif relation == "ends with":
                search.add_filter(column, "%%%s" % value, op="like")

            elif relation == "does not start with":
                search.add_filter(column, "%s%%" % value, op="not like")
            elif relation == "does not end with":
                search.add_filter(column, "%%%s" % value, op="not like")




            # integer / float comparisons
            elif relation == "is equal to":
                search.add_where("(\"%s\" = %s)" % (column, value) )
            elif relation == "is greater than":
                search.add_where("(\"%s\" > %s)" % (column, value) )
            elif relation == "is less than":
                search.add_where("(\"%s\" < %s)" % (column, value) )

            elif relation == "in":
                values = value.split("|")
                search.add_filters(column, values)
            elif relation == "not in":
                values = value.split("|")
                search.add_filters(column, values, op='not in')


            # date comparisons
            elif relation in ["is older than", "is before"]:
                cls._add_time_filter(search, column, value, '<=')
            elif relation in ["is newer than", "is after"]:
                cls._add_time_filter(search, column, value, '>=')
            elif relation in ["is on"]:
                date = Date(db_date = value)
                value = date.get_db_date()
                cls._add_time_filter(search, column, value, '>=')
                date.add_days(1)
                value2 = date.get_db_date()
                cls._add_time_filter(search, column, value2, '<')
            # time code
            elif relation == "is timecode before":
                timecode = TimeCode(timecode=value)
                frames = timecode.get_frames()
                search.add_filter(column, frames, op='<=')
            elif relation == "is timecode after":
                timecode = TimeCode(timecode=value)
                frames = timecode.get_frames()
                search.add_filter(column, frames, op='>=')
            elif relation == "is timecode equal":
                timecode = TimeCode(timecode=value)
                frames = timecode.get_frames()
                search.add_filter(column, frames, op='=')



            elif relation == "expression":
                op = values.get("%s_op" % prefix)
                if not op:
                    op = 'in'

                if op in ['in','not in']:
                    results = Search.eval(value)
                    # check here rather than letting add_relationship_filters nullifying the whole search
                    if results:
                        search.add_relationship_filters(results, op=op)
                    elif op == 'in':
                        search.set_null_filter()
                else:
                    if op == 'do not match':
                        op = 'not in'
                    else:
                        op = 'in'

                    ids = []
                    sobjects = Search( search.get_search_type() ).get_sobjects()
                    for sobject in sobjects:
                        result = Search.eval(value, sobject, single=True)
                        if result == True:
                            ids.append( sobject.get_id() )
                    if not ids:
                        search.set_null_filter()
                    else:
                        search.add_filters("id", ids, op=op)


            else:
                print("WARNING: relation [%s] not implemented" % relation)
                continue


            # handle the ops
            if filter_mode != 'custom':
                continue

            if ops == None:
                continue


            begin_idx = OriginalColumnFilter.add_ops(search, values_list, levels, ops, i, begin_idx)


        # handle the hardcoded 2nd level ops
        if filter_mode == 'custom' and ops != None:
            for count, op in enumerate(ops):
                level = levels[count]
                if level == 1:
                    search.add_op(op)
                    search.add_op('begin', upper_begin_idx)

        #print("FINAL: %s" % search.select.wheres)
        #print("SQL: %s" % search.get_statement())
        return num_enabled

    alter_sobject_search = classmethod(alter_sobject_search)


    def add_ops(search, values_list, levels, ops, i, begin_idx):
        '''add level 0 op if it is the end of the values list or if it encounters level 1 op'''
        if not levels:
            return begin_idx
        op = None
        # this is the end of values_list
        if i+1 == len(values_list):
            if levels[i-1] == 0:
                op = ops[-1]
        # this is level 1
        elif levels[i] == 1:
            # skip level 1
            op = ops[i-1]
        if op:
            search.add_op(op)
            search.add_op('begin', begin_idx)
            begin_idx = len(search.get_select().get_wheres())

        return begin_idx
    add_ops = staticmethod(add_ops)
