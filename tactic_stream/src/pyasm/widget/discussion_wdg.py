"""The former discussion column, projected through the existing note owner.

Source: legacy/src/pyasm/widget/discussion_wdg.py. HTML/CG Submission is excluded.
"""

from pyasm.common.errors import UnsupportedContract
from pyasm.widget.input_wdg import SelectWdg
from tactic.ui.widget.discussion_wdg import DiscussionElementWdg, DiscussionWdg as ProcessDiscussionWdg


class DiscussionWdg(ProcessDiscussionWdg):
    def preprocess(self):
        if str(self.get_option('include_submission')).lower() == 'true':
            raise UnsupportedContract(
                'Legacy Submission notes belong to the excluded pyasm.prod subsystem'
            )
        super().preprocess()

    def get_cell_value(self):
        self.preprocess()
        notes = self.get_notes()
        counts = {}
        for note in notes:
            if not note.get_parent_id():
                process = note.get_process() or 'publish'
                counts[process] = counts.get(process, 0) + 1
        choices = []
        for key in ('setting', 'append_setting'):
            setting = self.get_option(key)
            if setting:
                select = SelectWdg('context', setting=setting)
                select.set_dom_options()
                choices.extend(zip(select.values, select.labels))
        processes = {row['process']: row for row in DiscussionElementWdg.process_counts(self.parent, counts)}
        for value, label in choices:
            value = str(value)
            if not value:
                continue
            if '/' in value:
                raise UnsupportedContract(
                    'Legacy setting subcontexts are not supported; use the modern discussion widget with context'
                )
            processes.setdefault(value, dict(process=value, count=0))['label'] = str(label)
        return dict(
            text=str(sum(counts.values())), count=sum(counts.values()),
            search_key=self.parent.get_search_key() if self.parent else '',
            process=self.process or next(iter(processes), 'publish'),
            contexts=self.contexts or [], processes=list(processes.values()),
        )
