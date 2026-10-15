# Copyright (c) 2005-2012, Southpaw Technology. See LICENSE.TACTIC.
"""Original PluginUtil manifest catalog, with normalized and bounded paths."""
import os
from pathlib import Path

from pyasm.common import Environment, Xml


class PluginUtil:
    def __init__(self, **kwargs):
        self.base_dir = Path(kwargs.get('base_dir') or Environment.get_plugin_dir()).resolve().as_posix()

    def get_plugin_data(self, reldir):
        path = (Path(self.base_dir) / reldir).resolve()
        if not path.is_relative_to(Path(self.base_dir)):
            raise ValueError('Plugin path escapes its directory')
        xml = Xml()
        xml.read_file(str(path / 'manifest.xml'))
        node = xml.get_node('manifest/data')
        return {child.tag: child.text or '' for child in node} if node is not None else {}

    def get_plugins_data(self, plugin_type=None):
        plugins_data = {}
        for root, dirnames, basenames in os.walk(self.base_dir, followlinks=False):
            dirnames[:] = [name for name in dirnames if not (Path(root) / name).is_symlink()]
            if 'manifest.xml' not in basenames:
                continue
            reldir = Path(root).relative_to(self.base_dir).as_posix()
            data = self.get_plugin_data(reldir)
            if not plugin_type or data.get('type') == plugin_type:
                plugins_data[reldir] = data
        return plugins_data
