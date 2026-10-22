"""Original WorkHoursElementAction extracted from the presentation package.
Copyright (c) Southpaw Technology. Repository MIT license applies.
The legacy field names, current-login scoping, ST/OT categories and zero-delete
semantics are preserved. No alternative work-hours storage is introduced.
"""
from pyasm.command import DatabaseAction
from pyasm.common import Environment, jsonloads
from pyasm.search import SearchType
from dateutil import parser


class WorkHoursSemantics:
    OT = 'overtime'
    ST = 'regular'
    STT = 'regular_stt'
    ENT = 'regular_ent'
    OT_ROW = 'overtime_row'
    ST_ROW = 'regular_row'
    STT_ROW = 'starttime_row'
    ENT_ROW = 'endtime_row'
    ROW_DICT = {OT_ROW: OT, ST_ROW: ST, STT_ROW: STT, ENT_ROW: ENT}
    UNIT_DICT = {'hour': 3600, 'minute': 60}


class WorkHoursElementAction(DatabaseAction):

    def execute(self):
        value = self.get_value()
        if isinstance(value, dict):
            data = dict(value)
        elif value:
            data = jsonloads(value)
        else:
            data = {}

        task = self.sobject
        if not task:
            return
        parent = task.get_parent()

        self.unit = self.get_option("unit")
        if not self.unit:
            self.unit = "hour"
        if self.unit not in WorkHoursSemantics.UNIT_DICT:
            raise ValueError("Invalid work-hours display range or unit")

        self.use_straight_time = self.get_option("use_straight_time")
        if self.use_straight_time in (False, 'false'):
            self.use_straight_time = False
        else:
            self.use_straight_time = True

        if not parent:
            return

        user = Environment.get_user_name()
        entries = parent.get_related_sobjects("sthpw/work_hour")
        entries = [
            x for x in entries
            if x.get_value('task_code') == task.get_code()
            and x.get_value('login') == user
        ]

        entry_dict = {}
        for key, value in data.items():
            value = '' if value is None else str(value).strip()
            if self.use_straight_time:
                if not (key.startswith("day_") or key.startswith("otday_")):
                    continue
            else:
                if not (key.startswith("day_") or key.startswith("sttday_") or key.startswith("entday_")):
                    continue

            parts = key.split("_")
            if len(parts) != 4:
                continue
            _, year, month, day = parts
            date = "%s-%s-%s 00:00:00" % (year, month, day)

            exists = False
            matched_entry = None
            for entry in entries:
                entry_day = str(entry.get_value("day") or '')
                if entry_day == date or entry_day[:10] == date[:10]:
                    if self.use_straight_time:
                        if key.startswith("day_") and entry.get_value("category") in ('', WorkHoursSemantics.ST):
                            exists = True
                            matched_entry = entry
                            break
                        if key.startswith("otday_") and WorkHoursSemantics.OT == entry.get_value("category"):
                            exists = True
                            matched_entry = entry
                            break
                    else:
                        if (key.startswith("sttday_") or key.startswith("entday_")) and entry.get_value("category") in ('', WorkHoursSemantics.ST):
                            exists = True
                            matched_entry = entry
                            break

            entry = matched_entry
            if not exists:
                entry = entry_dict.get(date)
                if not entry:
                    entry = SearchType.create("sthpw/work_hour")
                    if parent:
                        entry.set_parent(parent)
                    entry.set_value("task_code", task.get_code())
                    entry.set_value("process", task.get_value('process'))
                    entry.set_value("day", date)
                    entry.set_user()
                    entry.set_project()

            if not self.use_straight_time:
                entry.set_value("project_code", task.get_value('project_code'))
                entry.set_value("category", WorkHoursSemantics.ST)
                if not value:
                    continue

                if key.startswith("entday_"):
                    date_part = key.replace('entday_', '').replace('_', '-')
                    time = parser.parse('%s %s' % (date_part, value.zfill(4)))
                    entry.set_value("end_time", time)
                elif key.startswith("sttday_"):
                    date_part = key.replace('sttday_', '').replace('_', '-')
                    time = parser.parse('%s %s' % (date_part, value.zfill(4)))
                    entry.set_value("start_time", time)

                entry_dict[date] = entry
            else:
                if value == '' or value == '0' or (value.replace('.', '', 1).isdigit() and float(value) == 0):
                    if exists:
                        entry.delete()
                elif exists and value == '%s' % entry.get_value('straight_time'):
                    continue
                else:
                    hours_val = float(value) / (60.0 if self.unit == 'minute' else 1.0)
                    entry.set_value("straight_time", hours_val)
                    entry.set_value("project_code", task.get_value('project_code'))
                    if key.startswith("otday_"):
                        entry.set_value("category", WorkHoursSemantics.OT)
                    else:
                        entry.set_value("category", WorkHoursSemantics.ST)
                    entry.commit()
                    if not exists:
                        entries.append(entry)

        for _, entry in entry_dict.items():
            st_time = str(entry.get_value('start_time') or '')
            end_time = str(entry.get_value('end_time') or '')
            if st_time and end_time:
                st_time_obj = parser.parse(st_time)
                end_time_obj = parser.parse(end_time)
                delta = (end_time_obj - st_time_obj).seconds / WorkHoursSemantics.UNIT_DICT[self.unit]
                entry.set_value("straight_time", delta)
            entry.commit()
