"""The actual Qt Handler service consumes the same native SSE/Command transport."""
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_transport
from PySide6.QtCore import QObject, Signal


class _HandlerApplication(QObject):
    project_changed = Signal(str, str)
    current_project_code = 'one'

    def __init__(self):
        super().__init__()
        self._settings = {'network/serverUpdateMode': 'sse'}

    def _write_settings(self):
        pass

    def request_authentication(self):
        self.expired = True


class HandlerEvents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'Basic')
        sys.path.append('D:/grav/Tactic Stream/TH')
        from PySide6.QtGui import QGuiApplication
        cls.owns_qt = QGuiApplication.instance() is None
        cls.qt = QGuiApplication.instance() or QGuiApplication([])
        test_transport.Transport.setUpClass()

    @classmethod
    def tearDownClass(cls):
        try:
            test_transport.Transport.tearDownClass()
        finally:
            sys.path.remove('D:/grav/Tactic Stream/TH')
            if cls.owns_qt:
                from PySide6.QtCore import QCoreApplication, QEvent
                cls.qt.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                cls.qt = None

    def wait(self, condition, timeout=5):
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            self.qt.processEvents()
            time.sleep(.005)
        self.assertTrue(condition(), 'Handler update condition timed out')

    def test_native_handler_push_switch_reconnect_and_subscriptions(self):
        from thlib.ui.server_updates import ServerUpdateService
        from thlib.environment import env_inst, env_server, env_mode
        from tactic_stream.server.api import Api
        from tactic_stream.server.server_updates import query_server_updates
        api = Api(test_transport.Transport.store)
        auth = dict(ticket=api.auth.get_ticket('admin', 'private-test-password'), project='one')
        app = _HandlerApplication()
        batches, reads, errors = [], [], []
        def query(**values):
            reads.append(values)
            return query_server_updates(**values)
        with (patch.object(env_inst, 'logins', {'admin': object()}),
              patch.object(env_inst, 'server_pool', SimpleNamespace(is_stopped=False)),
              patch.object(env_server, 'get_server', return_value=test_transport.Transport.url),
              patch.object(env_server, 'get_user', return_value='admin'),
              patch.object(env_server, 'get_ticket', return_value=auth['ticket']),
              patch.object(env_server, 'get_proxy', return_value={}),
              patch.object(env_mode, 'current_path', test_transport.Transport.temp.name),
              patch('tactic_stream.server.server_updates.query_server_updates', query)):
            service = ServerUpdateService(app)
            service.set_activity_notifications(False)
            service.set_search_type('contract/entity')
            service.batchReady.connect(batches.append)
            service.errorRaised.connect(lambda *value: errors.append(value))
            try:
                service.start()
                self.wait(lambda: service._stream is not None and not service.busy and bool(reads))
                self.assertTrue(any(row['searchType'] == 'contract/entity' for batch in batches for row in batch['cacheChanges']))
                self.assertIn('config/widget_config', service._stream.payload['search_types'])
                self.assertIn('config/custom_script', service._stream.payload['search_types'])
                self.assertIn('sthpw/connection', service._stream.payload['search_types'])
                from tactic_stream.server.server_events import read_event_clients
                self.wait(lambda: any(row.get('application') == 'TACTIC Handler'
                    for row in read_event_clients(test_transport.Transport.store.data_dir)))
                live = service._stream
                service.set_batch_delay(500)
                self.assertIs(service._stream, live, 'Batch delay must not reopen the stream')
                self.assertEqual(live.batch_delay, 500)
                batches.clear()
                baseline = len(reads)
                api.dispatch('update', [auth, 'contract/child?project=one&code=CH1', {'alternate_entity_code': 'A'}])
                until = time.monotonic() + 1.2
                self.wait(lambda: time.monotonic() >= until)
                self.assertEqual(len(reads), baseline, 'Unsubscribed type must not trigger a read')
                api.dispatch('update', [auth, 'contract/entity?project=one&code=A', {'name': 'HANDLER_SSE'}])
                self.wait(lambda: any(row['searchType'] == 'contract/entity' for batch in batches for row in batch['cacheChanges']))
                self.assertEqual(len(reads), baseline + 1)
                self.assertFalse(reads[-1]['include_activity'])
                self.assertFalse(reads[-1]['include_messages'])
                self.assertFalse(reads[-1]['include_cache_changes'])
                from pyasm.search.update_events import publish_changes
                publish_changes(test_transport.Transport.store.data_dir, [('one', 'config/widget_config')])
                self.wait(lambda: any(row['searchType'] == 'config/widget_config' for batch in batches for row in batch['cacheChanges']))
                old = service._stream
                service.set_search_type('contract/child')
                self.wait(lambda: service._stream is not old and not service.busy)
                self.assertFalse(old.active)
                service.set_tasks_visible(True)
                self.wait(lambda: not service.busy)
                self.assertIn('sthpw/task', service._stream.payload['search_types'])
                service.set_checkin_active(True)
                self.assertIsNone(service._stream)
                service.set_checkin_active(False)
                self.wait(lambda: not service.busy and service._stream is not None)
                service.stop()
                service.set_update_mode('poll')
                self.assertEqual(app._settings['network/serverUpdateMode'], 'poll')
            finally:
                service.shutdown()
                self.qt.processEvents()
            self.assertIsNone(service._stream)
            self.assertFalse(service.running)
            self.assertFalse(errors)
