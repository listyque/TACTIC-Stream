"""TACTIC XML view configuration; browser rendering belongs to Vue."""
from .widget_config import WidgetConfigException, WidgetConfig, WidgetConfigView
from .input_wdg import BaseInputWdg, TextWdg, TextAreaWdg, CheckboxWdg, SelectWdg, MultiSelectWdg, UploadWdg, HiddenWdg, InputException
from .table_element_wdg import BaseTableElementWdg, SimpleTableElementWdg, ArrayTableElementWdg, XmlWdg
from .table_element_wdg import CheckboxColWdg, SearchTypeElementWdg
from .file_wdg import ThumbWdg

__all__ = ['WidgetConfigException', 'WidgetConfig', 'WidgetConfigView',
           'BaseInputWdg', 'TextWdg', 'TextAreaWdg', 'CheckboxWdg', 'SelectWdg', 'MultiSelectWdg', 'UploadWdg', 'HiddenWdg', 'InputException',
           'BaseTableElementWdg', 'SimpleTableElementWdg', 'ArrayTableElementWdg', 'XmlWdg', 'ThumbWdg', 'CheckboxColWdg', 'SearchTypeElementWdg']

__all__.append("TaskCompletionWdg")


def __getattr__(name):
    # The modern statistic class imports the common table base from this package.
    if name == 'TaskCompletionWdg':
        from .statistic_wdg import TaskCompletionWdg
        return TaskCompletionWdg
    raise AttributeError(name)
