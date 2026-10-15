# Copyright (c) 2005-2008, Southpaw Technology. See LICENSE.TACTIC.
"""Original first-run directory contract on owned data, without demo databases."""
import os
from pathlib import Path
import sys

from pyasm.common import Config, Environment
from pyasm.common.config import initialize_config
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store


class FirstRunInit:
    def execute(self):
        self.copy_start()

    def copy_start(self):
        data = Path(Environment.get_data_dir(manual=True))
        with request_context(RequestContext(Store(data), 'admin')):
            if os.environ.get('TACTIC_CONFIG_PATH') or os.environ.get('TACTIC_TMP_CONFIG_PATH'):
                Config.get_config_path(no_exception=False)
            initialize_config(data, Config.get_config_path())
            Config.reload_config()
            # Existing data/configuration is retained; SQL installation is explicit.
            directories = [data / name for name in ('config', 'db', 'templates', 'dist')]
            directories += [Path(Environment.get_asset_dir()), Path(Environment.get_plugin_dir()),
                            Path(Environment.get_tmp_dir()), Path(Environment.get_tmp_dir()) / 'log']
            for path in directories:
                path.mkdir(parents=True, exist_ok=True)
            plugin_dir = Environment.get_plugin_dir()
            if plugin_dir not in sys.path:
                sys.path.insert(0, plugin_dir)
