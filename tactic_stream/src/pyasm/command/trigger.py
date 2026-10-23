"""TACTIC Trigger matching, in-process dispatch and deferred execution.

Adapted from pyasm/command/trigger.py; see LICENSE.TACTIC/source_manifest.json.
"""
import traceback

from pyasm.command.command import Command, HandlerCmd
from pyasm.common.common import Common, Container, jsondumps, jsonloads
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import Search, SearchType


class TriggerException(Exception):
    pass


class Trigger(Command):
    KEY = "Trigger:triggers2"
    STATIC_TRIGGER_KEY = "Trigger:static_trigger"
    STATIC_TRIGGER_COUNT = "Trigger:static_trigger_count"
    INTEGRAL_TRIGGER_KEY = "Trigger:integral_trigger"
    NOTIFICATION_KEY = "Trigger:notifications"
    TRIGGER_EVENT_KEY = "triggers:cache"
    NOTIFICATION_EVENT_KEY = "notifications:cache"
    STATIC_TRIGGERS = []
    INTEGRAL_TRIGGERS = []

    def __init__(self, **kwargs):
        self.caller = self.message = self.trigger_sobj = None
        self.input = {}
        self.output = {}
        self.ret_val = None
        # The original parent constructor replaces Trigger's kwargs with {}.
        super().__init__()

    def set_trigger_sobj(self, trigger_sobj):
        self.trigger_sobj = trigger_sobj

    def get_trigger_sobj(self):
        return self.trigger_sobj

    def get_trigger_data(self):
        data = self.trigger_sobj.get_value("data")
        return jsonloads(data) if data else {}

    def set_command(self, command):
        self.caller = command

    def get_command(self):
        return self.caller

    def set_caller(self, caller):
        self.caller = caller

    def get_caller(self):
        return self.caller

    def get_command_class(self):
        return self.caller.__class__.__name__

    def set_message(self, message):
        self.message = message

    def get_message(self):
        return self.message

    def set_event(self, event):
        self.message = event

    def get_event(self):
        return self.message

    def set_input(self, input):
        self.input = input

    def get_input(self):
        return self.input

    def set_output(self, output):
        self.output = output

    def get_output(self):
        return self.output

    def set_description(self, description):
        self.description = description

    def get_ret_val(self):
        return self.ret_val

    def set_ret_val(self, value):
        self.ret_val = value

    def execute(self):
        raise TriggerException("Must override execute function")

    @staticmethod
    def append_trigger(caller, trigger, event):
        trigger.set_caller(caller)
        trigger.set_event(event)
        Container.append_seq("Trigger:called_triggers", trigger)

    @classmethod
    def serialize_data(cls, data):
        try:
            return jsondumps(data)
        except (TypeError, ValueError):
            if isinstance(data, dict):
                from pyasm.search import SObject
                from pyasm.biz import Pipeline
                converted = {}
                for name, value in data.items():
                    if isinstance(value, SObject):
                        converted[name] = value.get_sobject_dict()
                    elif isinstance(value, Pipeline):
                        converted[name] = value.get_code()
                    else:
                        converted[name] = value
                try:
                    return jsondumps(converted)
                except (TypeError, ValueError):
                    pass
            raise UnsupportedContract("Non-JSON trigger inputs are not migrated") from None

    @classmethod
    def call_all_triggers(cls):
        triggers = Container.get("Trigger:called_triggers")
        Container.remove("Trigger:called_triggers")
        if not triggers:
            return
        prev_called_triggers = Container.get_seq("Trigger:prev_called_triggers")
        for trigger in triggers:
            try:
                input_json = cls.serialize_data(trigger.get_input())
                class_name = Common.get_full_class_name(trigger)
                if class_name == "pyasm.command.subprocess_trigger.SubprocessTrigger":
                    class_name = trigger.get_class_name()
                event = trigger.get_event()
                target_id = getattr(trigger, "script_path", None)
                if not target_id and isinstance(trigger, Trigger):
                    trigger_sobj = trigger.get_trigger_sobj()
                    if trigger_sobj is not None and trigger_sobj.get_base_search_type() == "sthpw/notification":
                        target_id = trigger_sobj.get_code() or trigger_sobj.get_id()
                if not target_id and isinstance(getattr(trigger, "data", None), dict):
                    target_id = jsondumps(trigger.data)
                key = (event, class_name, input_json, target_id) if target_id else (event, class_name, input_json)
                if key in prev_called_triggers:
                    continue
                prev_called_triggers.append(key)
                if not isinstance(trigger, Trigger):
                    handler_cmd = HandlerCmd(trigger)
                    handler_cmd.add_description(trigger.get_description())
                    trigger = handler_cmd
                trigger.get_transaction().set_sync(False)
                Trigger.execute_cmd(trigger, call_trigger=False)
                if Container.get("Trigger:called_triggers"):
                    cls.call_all_triggers()
            except Exception:
                # Original deferred errors do not cancel the committed caller or
                # the other triggers. Tracebacks keep failures visible in the log.
                traceback.print_exc()

    @classmethod
    def append_static_trigger(cls, trigger, startup=False):
        if startup:
            cls.STATIC_TRIGGERS.append(trigger)
        else:
            Container.append_seq(cls.STATIC_TRIGGER_KEY, trigger)

    @classmethod
    def get_static_triggers(cls):
        return Container.get_seq(cls.STATIC_TRIGGER_KEY)[:] + cls.STATIC_TRIGGERS

    @classmethod
    def get_static_triggers_by_event(cls, event, process=None):
        event_triggers = []
        for trigger in cls.get_static_triggers():
            trigger_process = trigger.get_value("listen_process", no_exception=True)
            if not trigger_process:
                trigger_process = trigger.get_value("process", no_exception=True)
            if trigger_process and not process:
                continue
            if process and not trigger_process:
                continue
            if trigger_process and process and trigger_process != process:
                continue
            if trigger.get_value("event") == event:
                event_triggers.append(trigger)
        return event_triggers

    @classmethod
    def append_integral_trigger(cls, trigger, startup=False):
        triggers = Container.get_seq(cls.INTEGRAL_TRIGGER_KEY)
        if startup:
            cls.INTEGRAL_TRIGGERS.append(trigger)
        else:
            triggers.append(trigger)

    @classmethod
    def get_integral_triggers(cls):
        return Container.get_seq(cls.INTEGRAL_TRIGGER_KEY)[:] + cls.INTEGRAL_TRIGGERS

    @classmethod
    def _get_triggers(cls, call_event, integral_only=False, project_code=None):
        if integral_only:
            trigger_key = '%s:integral' % cls.TRIGGER_EVENT_KEY
        else:
            trigger_key = cls.TRIGGER_EVENT_KEY
        notification_key = cls.NOTIFICATION_EVENT_KEY
        trigger_dict = Container.get(trigger_key)
        notification_dict = Container.get(notification_key)
        call_event_key = jsondumps(call_event)
        last_static_count = Container.get(cls.STATIC_TRIGGER_COUNT)
        static_trigger_sobjs = cls.get_static_triggers()
        current_static_count = len(static_trigger_sobjs)
        renew = last_static_count != current_static_count and (not integral_only)
        if trigger_dict == None or renew:
            trigger_dict = {}
            Container.put(trigger_key, trigger_dict)
            if integral_only:
                trigger_sobjs = cls.get_integral_triggers()
            else:
                trigger_sobjs = cls.get_db_triggers()
                if static_trigger_sobjs:
                    Container.put(cls.STATIC_TRIGGER_COUNT, current_static_count)
                    trigger_sobjs.extend(static_trigger_sobjs)
                integral_trigger_sobjs = cls.get_integral_triggers()
                if integral_trigger_sobjs:
                    trigger_sobjs.extend(integral_trigger_sobjs)
            for trigger_sobj in trigger_sobjs:
                trigger_event = trigger_sobj.get_value('event')
                trigger_process = trigger_sobj.get_value('process')
                trigger_stype = trigger_sobj.get_value('search_type', no_exception=True)
                listen_event = {}
                listen_event['event'] = trigger_event
                if trigger_process:
                    listen_event['process'] = trigger_process
                if trigger_stype:
                    listen_event['search_type'] = trigger_stype
                listen_key = jsondumps(listen_event)
                trigger_list = trigger_dict.get(listen_key)
                if trigger_list == None:
                    trigger_list = []
                    trigger_dict[listen_key] = trigger_list
                trigger_list.append(trigger_sobj)
        called_triggers = trigger_dict.get(call_event_key)
        if notification_dict == None:
            notification_dict = {}
            Container.put(notification_key, notification_dict)
            notification_sobjs = cls.get_notifications_by_event()
            for trigger_sobj in notification_sobjs:
                trigger_event = trigger_sobj.get_value('event')
                trigger_process = trigger_sobj.get_value('process')
                trigger_stype = trigger_sobj.get_value('search_type', no_exception=True)
                trigger_project = trigger_sobj.get_value('project_code', no_exception=True)
                listen_event = {}
                listen_event['event'] = trigger_event
                if trigger_process:
                    listen_event['process'] = trigger_process
                if trigger_stype:
                    listen_event['search_type'] = trigger_stype
                if trigger_project:
                    listen_event['project_code'] = trigger_project
                listen_key = jsondumps(listen_event)
                notification_list = notification_dict.get(listen_key)
                if notification_list == None:
                    notification_list = []
                    notification_dict[listen_key] = notification_list
                notification_list.append(trigger_sobj)
        key2 = call_event.copy()
        if not project_code:
            from pyasm.biz.project import Project
            project_code = Project.get_project_code()
        key2['project_code'] = project_code
        call_event_key2 = jsondumps(key2)
        matched_notifications = []
        for call_event_key in [call_event_key, call_event_key2]:
            matched = notification_dict.get(call_event_key)
            if matched:
                matched_notifications.extend(matched)
        combined_triggers = []
        if called_triggers:
            combined_triggers.extend(called_triggers)
        if matched_notifications:
            combined_triggers.extend(matched_notifications)
        return combined_triggers

    @classmethod
    def clear_db_cache(cls):
        # Invalidate both DB lists and their derived event maps.
        for key in list(Container.get_instance().get_data()):
            if isinstance(key, str) and any(key == prefix or key.startswith(prefix + ':')
                    for prefix in (cls.KEY, cls.TRIGGER_EVENT_KEY, cls.NOTIFICATION_KEY, cls.NOTIFICATION_EVENT_KEY)):
                Container.remove(key)

    @classmethod
    def get_db_triggers(cls):
        site_triggers = Container.get(cls.KEY)
        if site_triggers == None:
            search = Search('sthpw/trigger')
            search.add_project_filter()
            site_triggers = search.get_sobjects()
            Container.put(cls.KEY, site_triggers)
        from pyasm.biz.project import Project
        site = ''  # Multi-site storage is not ported; this is the original default site.
        project_code = Project.get_project_code()
        key = '%s:%s:%s' % (cls.KEY, project_code, site)
        project_triggers = Container.get(key)
        if project_triggers == None:
            if SearchType.get('config/trigger', no_exception=True) is not None:
                search = Search('config/trigger')
                project_triggers = search.get_sobjects()
            else:
                project_triggers = []
            Container.put(key, project_triggers)
        triggers = []
        triggers.extend(site_triggers)
        triggers.extend(project_triggers)
        return triggers

    @classmethod
    def call_by_key(cls, key, caller, output={}, forced_mode='', integral_only=False, project_code=None):
        event = key.get('event')
        triggers_sobjs = cls._get_triggers(key, integral_only, project_code=project_code)
        if not triggers_sobjs:
            return
        return cls._handle_trigger_sobjs(triggers_sobjs, caller, event, output, forced_mode=forced_mode, project_code=project_code)

    @classmethod
    def call(cls, caller, event, output={}, process=None, search_type=None, project_code=None, forced_mode=''):
        """message is part of a function name and so should
            not contain spaces """
        call_event = {}
        call_event['event'] = event
        if process:
            call_event['process'] = process
        if search_type:
            call_event['search_type'] = search_type
        from dataclasses import replace
        from pyasm.search.search import SObject, _context
        from pyasm.biz import Pipeline
        token = None
        if (isinstance(event, str) and event.startswith('process|') and isinstance(output, dict)
                and isinstance(output.get('sobject'), SObject)
                and isinstance(output.get('pipeline'), Pipeline)):
            # Keep identity, pooled connections and the transaction across project events.
            token = _context.set(replace(_context.get(), project=output['sobject'].get_project_code()))
        try:
            triggers_sobjs = cls._get_triggers(call_event, project_code=project_code)
            if not triggers_sobjs:
                return []
            return cls._handle_trigger_sobjs(triggers_sobjs, caller, event, output, forced_mode=forced_mode, project_code=project_code)
        finally:
            if token is not None:
                _context.reset(token)

    @classmethod
    def _handle_trigger_sobjs(cls, triggers_sobjs, caller, event, output, forced_mode='', project_code=None):
        allowed_modes = (
            'same process,same transaction',
            'same process,new transaction',
            'separate process,queued',
            'separate process,blocking',
            'separate process,non-blocking',
        )
        # Check unsupported branches before any selected handler executes.
        for trigger_sobj in triggers_sobjs:
            is_notification = trigger_sobj.get_base_search_type() == 'sthpw/notification'
            trigger_class = (
                ('pyasm.command.EmailTriggerTest' if forced_mode else 'pyasm.command.EmailTrigger2')
                if is_notification
                else trigger_sobj.get_value('class_name', no_exception=True)
            )
            is_email_trigger = is_notification or trigger_class in (
                'pyasm.command.EmailTrigger',
                'pyasm.command.EmailTrigger2',
                'pyasm.command.EmailTriggerTest',
            )
            mode = (
                (forced_mode or 'same process,new transaction')
                if is_email_trigger
                else (trigger_sobj.get_value('mode', no_exception=True) or 'same process,new transaction')
            )
            if mode not in allowed_modes:
                raise UnsupportedContract('Subprocess trigger execution mode is not supported: %s' % mode)
            from pyasm.search.transaction import Transaction
            transaction = Transaction.get()
            if transaction is not None and transaction.write_resource is not None and mode != 'same process,same transaction':
                raise UnsupportedContract('Atomic commands require synchronous triggers in the same transaction')
            if isinstance(trigger_class, str) and trigger_class:
                Common.resolve_class(trigger_class)
            if not is_email_trigger and (
                not trigger_class
                or trigger_class in ('tactic.command.PythonTrigger', 'tactic.command.python_cmd.PythonTrigger')
                or mode in ('separate process,queued', 'separate process,blocking', 'separate process,non-blocking')
            ):
                from tactic.command.python_cmd import check_script_execution
                check_script_execution(python=True)

        triggers = []
        for trigger_sobj in triggers_sobjs:
            is_notification = trigger_sobj.get_base_search_type() == 'sthpw/notification'
            trigger_class = (
                ('pyasm.command.EmailTriggerTest' if forced_mode else 'pyasm.command.EmailTrigger2')
                if is_notification
                else trigger_sobj.get_value('class_name')
            )
            is_email_trigger = is_notification or trigger_class in (
                'pyasm.command.EmailTrigger',
                'pyasm.command.EmailTrigger2',
                'pyasm.command.EmailTriggerTest',
            )
            mode = (
                (forced_mode or 'same process,new transaction')
                if is_email_trigger
                else (trigger_sobj.get_value('mode', no_exception=True) or 'same process,new transaction')
            )
            script_path = trigger_sobj.get_value('script_path', no_exception=True)
            if is_email_trigger:
                try:
                    trigger = Common.create_from_class_path(trigger_class)
                except ImportError:
                    traceback.print_exc()
                    raise
                trigger.set_trigger_sobj(trigger_sobj)
            elif mode in ('same process,same transaction', 'same process,new transaction'):
                if not trigger_class:
                    from tactic.command import PythonTrigger
                    trigger = PythonTrigger(script_path=script_path)
                elif isinstance(trigger_class, str):
                    try:
                        trigger = Common.create_from_class_path(trigger_class)
                    except ImportError:
                        traceback.print_exc()
                        raise
                else:
                    trigger = trigger_class()
            else:
                if not trigger_class:
                    target_class = 'tactic.command.PythonTrigger'
                    kwargs = {'script_path': script_path}
                elif isinstance(trigger_class, str):
                    Common.resolve_class(trigger_class)
                    target_class = trigger_class
                    kwargs = {}
                else:
                    target_class = f'{trigger_class.__module__}.{trigger_class.__qualname__}'
                    kwargs = {}
                trigger_data = trigger_sobj.get_value('data', no_exception=True)
                if trigger_data:
                    parsed = jsonloads(trigger_data) if isinstance(trigger_data, str) else trigger_data
                    if isinstance(parsed, dict):
                        kwargs.update(parsed)
                from pyasm.command.subprocess_trigger import SubprocessTrigger
                from pyasm.common import Environment
                trigger = SubprocessTrigger()
                trigger.set_mode(mode)
                resolved_project = project_code
                if not resolved_project:
                    from pyasm.biz.project import Project
                    resolved_project = Project.get_project_code()
                security = Environment.get_security()
                ticket = security.get_ticket_key() if security and hasattr(security, 'get_ticket_key') else None
                trigger_sobj_key = trigger_sobj.get_search_key() if hasattr(trigger_sobj, 'get_search_key') else None
                data = {
                    'project': resolved_project,
                    'ticket': ticket,
                    'class_name': target_class,
                    'kwargs': kwargs,
                    'event': event,
                }
                if trigger_sobj_key:
                    data['trigger_sobj_key'] = trigger_sobj_key
                if caller is not None and hasattr(caller, 'pipeline') and getattr(caller, 'pipeline', None) is not None:
                    try:
                        data['pipeline_code'] = caller.pipeline.get_code()
                    except Exception:
                        pass
                trigger.set_data(data)
            trigger.set_event(event)
            if isinstance(trigger, Trigger):
                trigger.set_trigger_sobj(trigger_sobj)
                trigger.set_caller(caller)
                trigger.set_message(event)
            triggers.append(trigger)
            input = output.copy() if output or output == {} else caller.get_info()
            trigger.set_input(input)
            trigger.set_output(input)
            trigger.set_description(trigger_sobj.get_value('description', no_exception=True))
            if mode != 'same process,same transaction':
                Container.append_seq('Trigger:called_triggers', trigger)
                continue
            try:
                trigger.set_ret_val(trigger.execute())
            except Exception as exc:
                if not Container.get('Trigger:error_reported'):
                    traceback.print_exc()
                    caller.errors.append('Trigger [%s] failed: %s' % (trigger.get_title(), str(exc)))
                    Container.put('Trigger:error_reported', True)
                raise
        return triggers

    @classmethod
    def get_by_event(cls, event, process=None):
        """get a list of triggers by event"""
        site_triggers = Container.get(cls.KEY)
        if site_triggers == None:
            search = Search('sthpw/trigger')
            search.add_project_filter()
            site_triggers = search.get_sobjects()
            Container.put(cls.KEY, site_triggers)
        from pyasm.biz.project import Project
        project_code = Project.get_project_code()
        key = '%s:%s' % (cls.KEY, project_code)
        project_triggers = Container.get(key)
        if project_triggers == None:
            if project_code not in ['admin', 'sthpw']:
                SearchType.get('config/trigger')
                search = Search('config/trigger')
                project_triggers = search.get_sobjects()
            else:
                project_triggers = []
            Container.put(key, project_triggers)
        triggers = []
        triggers.extend(site_triggers)
        triggers.extend(project_triggers)
        search_type = None
        event_triggers = []
        for trigger in triggers:
            trigger_process = trigger.get_value('listen_process', no_exception=True)
            if not trigger_process:
                trigger_process = trigger.get_value('process', no_exception=True)
            if trigger_process and (not process):
                continue
            if process and (not trigger_process):
                continue
            if trigger_process and process and (trigger_process != process):
                continue
            trigger_stype = trigger.get_value('search_type', no_exception=True)
            if trigger_stype and (not search_type):
                continue
            if search_type and (not trigger_stype):
                continue
            if trigger_stype and search_type and (trigger_stype != search_type):
                continue
            if trigger.get_value('event') == event:
                event_triggers.append(trigger)
        return event_triggers

    @classmethod
    def get_notifications_by_event(cls, event=None, process=None):
        triggers = Container.get(cls.NOTIFICATION_KEY)
        if triggers == None:
            search = Search('sthpw/notification')
            triggers = search.get_sobjects()
            Container.put(cls.NOTIFICATION_KEY, triggers)
        if event == None:
            return triggers
        from pyasm.biz.project import Project
        project_code = Project.get_project_code()
        event_triggers = []
        for trigger in triggers:
            trigger_process = trigger.get_value('process')
            if process and (not trigger_process):
                continue
            if trigger_process and (not process):
                continue
            if process and trigger_process and (trigger_process != process):
                continue
            trigger_project = trigger.get_value('project_code')
            if trigger_project and trigger_project != project_code:
                continue
            if trigger.get_value('event', no_exception=True) == event:
                event_triggers.append(trigger)
        return event_triggers


class SnapshotIsLatestTrigger(Trigger):

    # Since this trigger is run even on undo and is outside of the transaction
    # is should not be in the transaction log.  It is an inherent property
    # of the check-in
    def is_undoable(cls):
        return False
    is_undoable = classmethod(is_undoable)


    def execute(self):

        input = self.get_input()
        mode = input.get("mode")
        # NOTE: this could be run during update and insert of snapshot
        # during insert, for simple snapshot creation like server.create_snaphot()
        # during update, is_latest, is_current and update_versionless are handled together for check-in

        if mode in ['delete','retire']:
            sobject_dict = input.get("sobject")
            if sobject_dict.get('version') in (-1, 0):
                return
            context = sobject_dict.get("context")
            search_type = sobject_dict.get("search_type")
            search_code = sobject_dict.get("search_code")
            search_id = sobject_dict.get("search_id")

            search = Search("sthpw/snapshot")
            search.add_filter("context", context)
            search.add_filter("version", 0, op=">")
            search.add_filter("level_type", sobject_dict.get("level_type") or None)
            search.add_filter("level_id", sobject_dict.get("level_id") or None)
            search.add_order_by("timestamp desc")

            search.add_filter("search_type", search_type)
            if search_code:
                search.add_filter("search_code", search_code)
            else:
                search.add_filter("search_id", search_id)

            snapshots = search.get_sobjects()
            for i, snapshot in enumerate(snapshots):
                if i == 0:
                    if snapshot.get_value("is_latest") == False:
                        snapshot.set_value("is_latest", True)
                        snapshot.update_versionless("latest")
                        snapshot.commit()
                else:
                    if snapshot.get_value("is_latest") == True:
                        snapshot.set_value("is_latest", False)
                        snapshot.commit()

                # NOTE: not sure what to do with is_current when the
                # current snapshot is deleted

            return
        
        

        sobject_dict = input.get("sobject_dict")
        search_key = input.get("search_key")
        snapshot = Search.get_by_search_key(search_key)
        

        #print("mode: ", mode)
        #print("snapshot: ", snapshot.get("version"), snapshot.get("context"))
        #print("data: ", input.get("update_data").keys())
        #print("\n")


        # if the current snapshot is already the latest, don't do anything
        update_data = input.get("update_data")
        update_versionless = mode == 'update'

        if update_data.get("is_latest") == True:
            snapshot.set_latest(commit=True, update_versionless=update_versionless)


        if update_data.get("is_current") == True:
            snapshot.set_current(commit=True, update_versionless=update_versionless)
