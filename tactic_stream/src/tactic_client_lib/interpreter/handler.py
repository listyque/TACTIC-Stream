"""Minimal client interpreter Handler contract for trigger/pipeline handlers."""

__all__ = ['Handler']


class Handler(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.input = {}
        self.output = {}
        self.options = {}
        self.package = {}
        self.info = {}
        self.description = ""
        self.event = ""
        self.process_name = ""
        self.prev_command = None
        self.ret_val = None

    def set_prev_command(self, cmd):
        self.prev_command = cmd

    def set_options(self, options):
        self.options = options

    def get_options(self):
        return self.options

    def set_process_name(self, process_name):
        self.process_name = process_name

    def get_process_name(self):
        return self.process_name

    def set_package(self, package):
        self.package = package

    def get_package(self):
        return self.package

    def set_event(self, event):
        self.event = event

    def get_event(self):
        return self.event

    def set_input(self, input):
        self.input = input

    def get_input(self):
        return self.input

    def get_input_data(self):
        return self.input

    def set_output(self, output):
        self.output = output

    def get_output(self):
        return self.output

    def get_output_data(self):
        return self.output

    def set_description(self, description):
        self.description = description

    def get_description(self):
        return self.description

    def get_title(self):
        return "%s.%s" % (self.__module__, self.__class__.__name__)

    def get_info(self):
        return self.info

    def set_ret_val(self, value):
        self.ret_val = value

    def get_ret_val(self):
        return self.ret_val

    def execute(self):
        pass
