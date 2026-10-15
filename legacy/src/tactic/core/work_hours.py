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
        if value:
            data = jsonloads(value)
        else:
            data = {}

        task = self.sobject
        parent = task.get_parent()

        self.unit = self.get_option("unit")
        if not self.unit:
            self.unit = "hour"

        self.use_straight_time = self.get_option("use_straight_time")
        #self.use_straight_time = 'false'
        if self.use_straight_time == 'false':
            self.use_straight_time = False
        else:
            self.use_straight_time = True

        # Do this for now. EXIT if the parent of task can't be found..
        if not parent:
            return

        # TODO: make it work if self.sobject is not an instance of a Task
        use_task_code = True

        # match assigned to avoid deleting work hours entries made on the same task by other users
        user = Environment.get_user_name()
        entries = parent.get_related_sobjects("sthpw/work_hour")

        # filter out just for this task
        if use_task_code:
            entries = [x for x in entries if x.get_value('task_code') == task.get_code() and x.get_value('login') == user]

        entry_dict = {}
        for key, value in data.items():
            if self.use_straight_time:
                if not (key.startswith("day_") or key.startswith("otday_")):
                    continue
            else:
                if not (key.startswith("day_") or key.startswith("sttday_") or key.startswith("entday_")):
                    continue
                start_value = data


            tmp, year, month, day = key.split("_")
            date = "%s-%s-%s 00:00:00" % (year,month,day)
            #OVER_TIME_TYPE = 'ot'

            exists = False
            # TODO: we should allow multiple entiries per task per day and just
            # have a special UI to edit individual entries post creation.
            for entry in entries:
                entry_day = entry.get_value("day")
                if entry_day == date:
                    if self.use_straight_time:

                        if key.startswith("day_"):
                            if entry.get_value("category") in ['',WorkHoursSemantics.ST] :
                                exists = True
                                break
                        if key.startswith("otday_"):
                            if WorkHoursSemantics.OT == entry.get_value("category"):
                                exists = True
                                break
                    else:
                         # only supports regular hours for start and end time
                         if key.startswith("sttday_"):
                            if entry.get_value("category") in ['',WorkHoursSemantics.ST] :
                                exists = True
                                break
                         elif key.startswith("entday_"):
                            if entry.get_value("category") in ['',WorkHoursSemantics.ST] :
                                exists = True
                                break


            if not exists:
                entry = entry_dict.get(date)
                if not entry:
                    # create a new one
                    entry = SearchType.create("sthpw/work_hour")
                    if parent:
                        entry.set_parent(parent)
                    entry.set_value("task_code", task.get_code() )
                    entry.set_value("process", task.get_value('process'))
                    entry.set_value("day", date)
                    entry.set_user()
                    entry.set_project()

            if not self.use_straight_time:
                # only enter standard time for now
                entry.set_value("project_code", task.get_value('project_code'))
                entry.set_value("category", WorkHoursSemantics.ST)
                if not value:
                    continue

                date_part = ''
                if key.startswith("entday_"):
                    date_part = key.replace('entday_','')
                    date_part = date_part.replace('_','-')
                    value = value.zfill(4)
                    time = parser.parse('%s %s' %(date_part, value))
                    entry.set_value("end_time", time)

                elif key.startswith("sttday_"):
                    date_part = key.replace('sttday_','')
                    date_part = date_part.replace('_','-')
                    value = value.zfill(4)
                    time = parser.parse('%s %s' %(date_part, value))
                    entry.set_value("start_time", time)

                entry_dict[date] = entry

                #entry.commit()

            else:
                if value == '' or value == '0':
                    if exists:
                        entry.delete()

                elif value == '%s'% entry.get_value('straight_time'):
                    # prevent commit the same value again
                    continue
                else:
                    #
                    entry.set_value("straight_time", value)
                    entry.set_value("project_code", task.get_value('project_code'))

                    if key.startswith("otday_"):
                        entry.set_value("category", WorkHoursSemantics.OT)
                    else:
                        entry.set_value("category", WorkHoursSemantics.ST)


                    entry.commit()

            for key, entry in entry_dict.items():

                # set the straight_time as well
                st_time = str(entry.get_value('start_time'))
                end_time = str(entry.get_value('end_time'))
                if st_time and end_time:
                    st_time_obj = parser.parse(st_time)
                    end_time_obj = parser.parse(end_time)

                    delta = (end_time_obj - st_time_obj).seconds / WorkHoursSemantics.UNIT_DICT[self.unit]
                    entry.set_value("straight_time", delta)

                entry.commit()








