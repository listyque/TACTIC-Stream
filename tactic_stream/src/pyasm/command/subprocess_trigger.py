"""Async/queued and separate-process trigger wrappers for TACTIC Stream."""
from __future__ import annotations

import traceback

from pyasm.command.command import Command
from pyasm.common import Common, Container
from pyasm.search import Search
from pyasm.security import Site
from tactic_client_lib import TacticServerStub
from tactic_client_lib.interpreter import Handler

__all__ = ['SubprocessTrigger', 'QueueTrigger', 'ScriptTrigger']


class SubprocessTrigger(Handler):
    """Calls a trigger via queue or deferred execution transaction."""

    def __init__(self):
        self.mode = 'same process,new transaction'
        self.info = {}
        self.data = {}
        self.class_name = None
        super().__init__()

    def set_data(self, data):
        self.data = dict(data or {})
        self.class_name = self.data.get('class_name')
        kwargs = self.data.get('kwargs')
        if isinstance(kwargs, dict) and kwargs.get('result'):
            self.info['result'] = kwargs.get('result')
        elif self.mode in ('separate process,queued', 'separate process,non-blocking', 'separate process,blocking'):
            self.info.setdefault('result', 'wait')

    def get_info(self):
        return self.info

    def get_class_name(self):
        return self.class_name

    def set_mode(self, mode):
        self.mode = mode
        if self.mode in ('separate process,queued', 'separate process,non-blocking', 'separate process,blocking'):
            self.info.setdefault('result', 'wait')

    def execute(self):
        input_data = self.get_input_data()
        data = dict(self.data or {})

        site = Site.get_site()
        if site and not data.get('site'):
            data['site'] = site

        result = True

        if self.mode == 'separate process,queued':
            kwargs = data.get('kwargs') or {}
            priority = kwargs.get('priority') or 99999
            description = kwargs.get('description') or self.description or 'Trigger'
            queue_type = kwargs.get('trigger') or 'trigger'

            queue_kwargs = {
                'input_data': input_data,
                'data': data,
            }
            from tactic.command import Queue
            Queue.add(
                'pyasm.command.QueueTrigger',
                queue_kwargs,
                queue_type=queue_type,
                priority=priority,
                description=description,
            )
            result = 'wait'
        else:
            trigger = ScriptTrigger()
            trigger.set_data(data)
            trigger.set_input(input_data)
            trigger.execute()
            info = trigger.get_info() or {}
            if info.get('result') is not None:
                result = info.get('result')

        if 'result' not in self.info or self.mode != 'separate process,queued':
            self.info['result'] = result


class QueueTrigger(Command):
    """Command executed from sthpw/queue to run a deferred ScriptTrigger."""

    def execute(self):
        from pyasm.command import Workflow
        Workflow().init(quiet=True)

        input_data = self.kwargs.get('input_data')
        data = self.kwargs.get('data')

        trigger = ScriptTrigger()
        trigger.set_input(input_data)
        trigger.set_data(data)
        trigger.execute()

        info = trigger.get_info()
        result = info.get('result')
        if result == 'error':
            message = info.get('message')
            raise Exception(message)


class ScriptTrigger(Handler):
    """Executes the underlying trigger class or PythonTrigger and updates workflow status."""

    def __init__(self):
        self.mode = 'same process,new transaction'
        self.info = {}
        self.data = {}
        self.class_name = None
        self.kwargs = {}
        super().__init__()

    def get_info(self):
        return self.info

    def set_data(self, data):
        self.data = dict(data or {})

    def execute(self):
        self.class_name = self.data.get('class_name')
        assert self.class_name
        self.kwargs = dict(self.data.get('kwargs') or {})

        trigger = Common.create_from_class_path(self.class_name, kwargs=self.kwargs)
        if not getattr(trigger, 'kwargs', None) and self.kwargs:
            trigger.kwargs = dict(self.kwargs)
        script_path = self.kwargs.get('script_path')
        if script_path and hasattr(trigger, 'set_script_path') and not getattr(trigger, 'script_path', None):
            trigger.set_script_path(script_path)
        trigger_sobj_key = self.data.get('trigger_sobj_key')
        if trigger_sobj_key and hasattr(trigger, 'set_trigger_sobj'):
            try:
                trigger_sobj = Search.get_by_search_key(trigger_sobj_key)
                if trigger_sobj is not None:
                    trigger.set_trigger_sobj(trigger_sobj)
            except Exception:
                pass
        event = self.data.get('event')
        if event and hasattr(trigger, 'set_event'):
            trigger.set_event(event)

        input_data = self.get_input_data()
        trigger.set_input(input_data)
        if hasattr(trigger, 'set_output'):
            trigger.set_output(input_data)

        try:
            ret_val = trigger.execute()
            info = trigger.get_info() if hasattr(trigger, 'get_info') else {}
            result = info.get('result') if isinstance(info, dict) else None
            if result is None and ret_val is not None:
                result = ret_val
            if result is not None:
                if result in ['true', True]:
                    result = 'complete'
                elif result in ['false', False]:
                    result = 'revise'
                self.set_pipeline_status(result)
                self.info['result'] = result
            else:
                self.set_pipeline_status('complete')
                self.info['result'] = 'complete'
        except Exception as exc:
            self.set_pipeline_status('revise', {'error': str(exc)})
            traceback.print_exc()
            self.info['result'] = 'error'
            self.info['message'] = str(exc)

    def set_pipeline_status(self, status, data=None):
        input_data = self.get_input_data()
        if not isinstance(input_data, dict):
            return
        sobject = input_data.get('sobject')
        if not sobject:
            return
        search_key = (
            sobject.get('__search_key__')
            if isinstance(sobject, dict)
            else (sobject.get_search_key() if hasattr(sobject, 'get_search_key') else None)
        )
        process = input_data.get('process')
        if not search_key or not process:
            return
        try:
            from pyasm.command import Trigger, Workflow
            from pyasm.biz import Pipeline
            Workflow().init(quiet=True)
            sobj = Search.get_by_search_key(search_key)
            if sobj is None:
                return
            pipeline_code = self.data.get('pipeline_code')
            if not pipeline_code and isinstance(sobject, dict):
                pipeline_code = sobject.get('pipeline_code')
            if not pipeline_code:
                pipeline_code = sobj.get_value('pipeline_code', no_exception=True)
            if not pipeline_code:
                return
            pipeline = Pipeline.get_by_code(pipeline_code)
            if pipeline is None:
                return
            Trigger.call(
                self,
                'process|%s' % status,
                {
                    'pipeline': pipeline,
                    'sobject': sobj,
                    'process': process,
                    'status': status,
                    'data': dict(data or {}),
                },
            )
        except Exception:
            pass
