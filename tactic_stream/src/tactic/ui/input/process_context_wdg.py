# Copyright (c) 2009 Southpaw Technology. See LICENSE.TACTIC.
"""Original form process/context choices; HTML and inline cell switching excluded."""
from pyasm.search import Search, SearchKey
from pyasm.biz import Pipeline
from pyasm.widget import BaseInputWdg, SelectWdg, TextWdg
from pyasm.common.errors import UnsupportedContract
from tactic.core.context_actions import SubContextAction


class ProcessInputWdg(BaseInputWdg):
    def get_input(self):
        from tactic.ui.panel import EditWdg
        if not isinstance(self.get_parent_wdg(), EditWdg):
            raise UnsupportedContract('Inline process input switching is not migrated')
        self.in_edit_wdg = True
        self.pipeline_codes, self.pipelines = [], []
        sobject = self.get_current_sobject()
        parent = sobject.get_parent()
        if not parent and self.get_option('parent_key'):
            parent = SearchKey.get_by_search_key(self.get_option('parent_key'))
        if not parent:
            # Original EditWdg renders no process control without a parent pipeline.
            return None
        if not parent.has_value('pipeline_code'):
            text = TextWdg(self.get_input_name())
            text.set_value(sobject.get_value(self.get_name()))
            return text
        pipe_code = parent.get_value('pipeline_code')
        if not pipe_code:
            return None
        pipeline = Pipeline.get_by_code(pipe_code)
        if not pipeline:
            raise ValueError('Pipeline not found: ' + pipe_code)
        self.pipeline_codes, self.pipelines = [pipe_code], [pipeline]
        select = SelectWdg(self.get_input_name())
        select.add_empty_option('-- Select a %s --' % self.get_name())
        processes = pipeline.get_processes(recurse=True, type=['manual', 'approval', 'node'])
        values, labels = [], []
        for process in processes:
            process_name = process.get_full_name() if process.is_from_sub_pipeline() else process.get_name()
            if self.get_option('context') == 'true':
                for context in pipeline.get_output_contexts(process.get_name()):
                    if context not in values:
                        values.append(context)
                        labels.append(context)
            elif process_name not in values:
                # Source accidentally checked the input name rather than the process name.
                values.append(process_name)
                labels.append(process_name)
        select.set_option('values', values)
        select.set_option('labels', labels)
        value = sobject.get_value(self.get_name())
        if self.get_name() == 'context' and value and '/' in value and value not in values:
            select.append_option(value, value)
        if value:
            select.set_value(value)
        return select


class SubContextInputWdg(TextWdg):
    def get_input(self):
        sobject = self.get_current_sobject()
        context = sobject.get_value('context') if sobject else ''
        if context and '/' in context:
            base, subcontext = context.split('/', 1)
            self.set_value(subcontext)
        return self


class ReviewProcessInputWdg(SelectWdg):
    def get_input(self):
        pipeline_code = self.kwargs.get('pipeline_code')
        values, labels = [], []
        if pipeline_code:
            search = Search('sthpw/pipeline')
            search.add_filter('code', pipeline_code)
            pipeline = search.get_sobject()
            if not pipeline:
                raise ValueError('Pipeline not found: ' + pipeline_code)
            processes = pipeline.get_processes(recurse=True, type=['manual', 'approval', 'node'])
            for process in processes:
                process_name = process.get_full_name() if process.is_from_sub_pipeline() else process.get_name()
                if self.get_option('context') == 'true':
                    for context in pipeline.get_output_contexts(process.get_name()):
                        if context not in values:
                            values.append(context)
                            labels.append(context)
                else:
                    values.append(process_name)
                    labels.append(process_name)
        self.add_empty_option('--- Select ---')
        self.set_option('values', '|'.join(values))
        self.set_option('labels', '|'.join(labels))
        return self
