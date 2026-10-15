"""TACTIC Command pipeline in a request/Batch context.

Adapted from pyasm/command/command.py; see LICENSE.TACTIC/source_manifest.json.
Original dependent Pipeline actions run through HandlerCmd after the caller commits.
Web UI checks are not ported.
"""
import logging

from pyasm.common.common import Base, Common, Container, SecurityException, TacticException
from pyasm.common.errors import UnsupportedContract
from pyasm.search.transaction import Transaction


class CommandException(TacticException):
    pass


class CommandExitException(TacticException):
    pass


class Command(Base):
    TOP_CMD_KEY = "Command:top_cmd"

    def __init__(self, **kwargs):
        self.errors = []
        self.description = ""
        self.info = {}
        self.response = ""
        self.sobjects = []
        self.pipeline_code = self.process_name = self.event_name = None
        self.kwargs = kwargs
        self.transaction = self.update = None

    def can_run(self, source="api"):
        return True

    def requires_key(self):
        return False

    def get_errors(self):
        return self.errors

    def get_description(self):
        return self.description

    def add_description(self, description):
        if self.description:
            self.description += "\n%s" % description
        else:
            self.description += "%s" % description

    def set_response(self, response):
        self.response = response

    def get_sobjects(self):
        return self.sobjects

    def is_update(self):
        return self.update

    def get_title(self):
        return Common.get_full_class_name(self)

    def check(self):
        return True

    def check_security(self):
        return True

    def preprocess(self):
        pass

    def get_data(self):
        pass

    def execute(self):
        raise CommandException("Must override execute function")

    def postprocess(self):
        pass

    def start(self):
        pass

    def rollback(self):
        pass

    def commit(self):
        pass

    def get_info(self, key=None):
        return self.info if not key else self.info.get(key)

    def set_transaction(self, transaction):
        self.transaction = transaction
        return self.transaction

    def get_transaction(self):
        if not self.transaction:
            self.transaction = Transaction.get(create=True)
        return self.transaction

    def execute_transaction(self, call_trigger=True):
        Command.execute_cmd(self, call_trigger=call_trigger)

    @classmethod
    def execute_cmd(cls, cmd, call_trigger=True):
        if not isinstance(cmd, Command):
            raise Exception("Cannot execute command.  Must be derived from Command class.")
        # Covers every hook, including check_security/start and post-commit listeners.
        running = Container.append_seq("Command:executing", cmd)
        try:
            if not cmd.check_security():
                raise SecurityException()
            # Original Batch ignores check(); the old web UI branch is not ported.
            transaction = cmd.get_transaction()
            transaction.register(cmd)
            top_cmd_seq = Container.get_seq(cmd.TOP_CMD_KEY)
            top_cmd_seq.append(cmd)
            ret_val = None
            try:
                transaction.set_command_class(Common.get_full_class_name(cmd))
                cmd.preprocess()
                cmd.get_data()
                ret_val = cmd.execute()
                if ret_val is not None:
                    cmd.info = ret_val
                cmd.postprocess()
            except CommandExitException:
                if cmd != top_cmd_seq[0]:
                    raise
                transaction.rollback()
                Container.put(cmd.TOP_CMD_KEY, None)
                raise
            except KeyboardInterrupt:
                # Cancellation must not publish a partially built project.
                if cmd == top_cmd_seq[0]:
                    transaction.rollback()
                    Container.put(cmd.TOP_CMD_KEY, None)
                raise
            except Exception as exc:
                if cmd != top_cmd_seq[0]:
                    raise
                transaction.rollback()
                # Failed nested commands leave entries above the root command.
                Container.put(cmd.TOP_CMD_KEY, None)
                cmd.errors.append(str(exc))
                cls._log_exception(cmd, exc)
                raise
            else:
                is_top = cmd == top_cmd_seq[0]
                if cmd == top_cmd_seq[-1]:
                    description = cmd.get_description()
                    if description:
                        transaction.add_description(description)
                    try:
                        transaction.commit()
                    except Exception as exc:
                        if not transaction.is_in_transaction():
                            Container.put(cmd.TOP_CMD_KEY, None)
                            cls._log_exception(cmd, exc)
                        raise
                    top_cmd_seq.pop()
                if is_top:
                    cmd.notify_listeners()
                    from pyasm.command.trigger import Trigger
                    # call_trigger is unused in the original implementation, too.
                    Trigger.call_all_triggers()
            return ret_val
        finally:
            running.pop()

    @staticmethod
    def _log_exception(cmd, exception):
        if cmd.kwargs.get('log_exception') is False:
            return
        try:
            from pyasm.search.exception_log import ExceptionLog
            ExceptionLog.log(exception)
        except Exception:
            # Diagnostics failure must never replace the command's original error.
            logging.getLogger(__name__).exception('Could not persist the command exception')

    @classmethod
    def is_undoable(cls):
        return True

    def set_process(self, process_name):
        self.process_name = process_name

    def get_process(self):
        return self.process_name

    def set_pipeline_code(self, pipeline_code):
        self.pipeline_code = pipeline_code

    def get_pipeline_code(self):
        return self.pipeline_code

    def set_event_name(self, event_name):
        self.event_name = event_name

    def get_event_name(self):
        return self.event_name

    def set_as_approved(self):
        '''convinience function that sets task for this process as approved'''
        from pyasm.biz import Task
        self.set_event_name("task/approved")

        # get the task associated with this process
        tasks = Task.get_by_sobjects(self.sobjects, self.process_name)

        for task in tasks:
            task.set_value("status", "Approved")
            task.commit()

    def notify_listeners(self):
        '''The command must have operated on an sobject with a pipeline and
        the operation must have been done on a process in that pipeline'''

        # find the sobject that this command operated on
        sobjects = self.get_sobjects()
        if not sobjects:
            return

        sobject = sobjects[0]
        if not sobject.has_value("pipeline_code"):
            return


        # we have sufficient information
        current_pipeline_code = self.get_pipeline_code()
        if not current_pipeline_code:
            current_pipeline_code = sobject.get_value("pipeline_code")


        current_process = self.get_process()
        event = self.get_event_name()
        if not current_pipeline_code or not current_process:
            return
        # get the pipelne (for in pipeline process)
        from pyasm.biz import Pipeline
        pipeline = Pipeline.get_by_code(current_pipeline_code)
        if pipeline is None:
            raise CommandException("Pipeline [%s] does not exist" % current_pipeline_code)
        self.handle_pipeline(pipeline, current_process, event)

    def handle_pipeline(self, pipeline, current_process, event):

        from pyasm.common import Xml
        from tactic.command.python_cmd import check_script_execution
        if pipeline is None:
            raise CommandException('Pipeline does not exist')

        # find the output processes
        output_processes = pipeline.get_output_processes(current_process)
        for process in output_processes:
            action_node = process.get_action_node(event, scope="dependent")
            if action_node is None:
                continue

            # get the action class.
            handler_cls = Xml.get_attribute(action_node, "class")
            if not handler_cls:
                continue



            # execute handler
            check_script_execution(require_transaction=False)
            handler = Common.create_from_class_path(handler_cls)

            # DEPRECATED
            handler.set_prev_command(self)

            # set the options
            options = process.get_action_options(event, scope="dependent")
            handler.set_options(options)

            # send some info to the executed handler
            handler.set_process_name(process.get_name() )

            # create a package
            #package = { 'foo': 'whatever'}
            #handler.set_package(package)

            # transfer outputs to inputs.  This allows a command to deliver
            # from one process to another
            input = self.get_info()
            handler.set_input(input)
            # By default, inputs travel through
            handler.set_output(input)


            # execute the handler command wrapper
            handler_cmd = HandlerCmd(handler)
            handler_cmd.set_event_name(event)
            handler_cmd.set_process(process.get_name() )
            handler_cmd.set_pipeline_code(pipeline.get_code() )
            Command.execute_cmd(handler_cmd)

class HandlerCmd(Command):
    """Original wrapper for a handler executed in its own Command transaction."""

    def __init__(self, handler):
        self.handler = handler
        super().__init__()

    def get_info(self):
        return self.handler.get_input()

    def get_input(self):
        return self.handler.get_input()

    def execute(self):
        self.handler.execute()
