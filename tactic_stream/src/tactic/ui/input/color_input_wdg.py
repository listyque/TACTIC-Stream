# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Original ColorInputWdg value preparation, without HTML/JavaScript rendering."""
from random import choice

from pyasm.widget import BaseInputWdg, TextWdg


class ColorInputWdg(BaseInputWdg):
    ARGS_KEYS = {}

    def __init__(self, name=None, **kwargs):
        super().__init__(name or kwargs.get('name'), **kwargs)
        self.input = TextWdg(self.get_input_name())

    def set_input(self, input):
        self.input = input
        self.input.set_name(self.get_input_name())

    def get_input(self):
        value = self.get_value()
        start_color = self.get_option('start_color')
        if not value or start_color:
            if not start_color or start_color == 'random':
                colors = ['#bccfd7', '#bcd7cf', '#d7bccf', '#d7cfbc', '#cfbcd7', '#cfd7bc']
            else:
                # The original comma check leaves a single configured color broken.
                colors = [color.strip() for color in start_color.split(',') if color.strip()]
            if colors:
                value = choice(colors)
        self.input.set_name(self.get_input_name())
        self.input.set_value(value)
        return self.input
