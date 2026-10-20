"""Original bid/actual table schedule using the portable timeline projection."""
import json
from tactic.ui.table.gantt_element_wdg import GanttElementWdg


class GanttWdg(GanttElementWdg):
    ARGS_KEYS = dict.fromkeys(('bid_edit','actual_edit','width','cal_margin'), {})

    def preprocess(self):
        for flag in ('bid_edit', 'actual_edit'):
            if self.get_option(flag) not in ('', True, False, 'true', 'false'):
                raise ValueError('Invalid schedule editing option')
        options = []
        for prefix, color in (('bid', '#33F'), ('actual', '#7abc14')):
            options.append(dict(start_date_col=prefix + '_start_date', end_date_col=prefix + '_end_date',
                color=color, edit=self.get_option(prefix + '_edit') in (True, 'true')))
        self.options['options'] = json.dumps(options)
        super().preprocess()
