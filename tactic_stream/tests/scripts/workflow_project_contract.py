"""Unchanged process lookup in the source and native Workflow runtimes."""
from pyasm.biz import Pipeline, Project
from pyasm.command.workflow import BaseProcessTrigger
from pyasm.search import Search


def run(case):
    pipeline = Search.get_by_code('sthpw/pipeline', case['pipeline'])
    handler = BaseProcessTrigger()
    handler.input = dict(pipeline=pipeline, process='work')
    direct = pipeline.get_process_sobject('work')
    callback = handler.get_process_sobj(pipeline, 'work')
    return dict(project=Project.get_project_code(), owner=pipeline.get_value('project_code'),
                direct=direct.get_code() if direct else None,
                callback=callback.get_code() if callback else None)
