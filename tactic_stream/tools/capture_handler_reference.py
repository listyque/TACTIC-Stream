"""Capture current Handler QML offline without touching its source or settings.

D:/Python314/python.exe -B tools/capture_handler_reference.py
"""
from pathlib import Path
from datetime import datetime
from html import escape
import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HANDLER = Path(os.environ.get("TACTIC_HANDLER_ROOT", "D:/grav/Tactic Stream/TH"))
OUTPUT = ROOT / ".screenshots/handler-current"


def capture_main(debug_only=False, performance_only=False, shelf_only=False, editor_only=False, activity_only=False, connection_only=False, notifications_only=False, tabs_only=False, progress_only=False, toasts_only=False, messages_only=False, menus_only=False, configuration_only=False):
    from PySide6.QtCore import QEventLoop, QObject, QPoint, QPointF, QTimer, Qt
    from PySide6.QtGui import QFontInfo, QWheelEvent
    from PySide6.QtQml import QQmlExpression, QQmlEngine
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from thlib.ui import application
    from thlib.ui.models import NavigationEntry
    from thlib.ui.controllers.types import SearchTabSession, SectionSession
    from thlib.ui.workspace_models.results_types import WorkspaceNode
    from thlib.environment import env_server
    from thlib.tactic_classes import Project
    from thlib.ui.quick_filter_editor import QuickFilterEditorController

    runtime = []
    original = application.build_application_runtime

    def build(*args, **kwargs):
        result = original(*args, **kwargs)
        runtime.append(result)
        return result

    application.build_application_runtime = build
    failures = []
    ticket = patch.object(env_server, "get_ticket", return_value="offline-screenshot-fixture")
    ticket.start()
    filters = patch.object(QuickFilterEditorController, "ensure_current")
    filters.start()

    def settle():
        loop = QEventLoop()
        QTimer.singleShot(450, loop.quit)
        loop.exec()

    def save(window, name):
        settle()
        picture = window.grabWindow()
        if picture.isNull() or not picture.save(str(OUTPUT / (name + ".png"))):
            raise RuntimeError("Failed to capture " + name)
        print(name, picture.width(), picture.height(), flush=True)

    def shoot(app):
        try:
            window = next(w for w in app.allWindows()
                          if w.title().startswith("TACTIC-Handler"))
            window.resize(1440, 1000)
            controller = runtime[0].controller
            controller._current_project_code = "demo"
            controller._current_project_title = "UI Test"
            tab = SearchTabSession(tab_id="collection", title="Collection", loaded=True,
                                   view_mode="continious", total=1)
            section = SectionSession(entry_key="demo/collection", title="Collection",
                                     accent="#79a7bf", search_type="demo/collection",
                                     tabs=[tab], current_tab_id=tab.tab_id)
            controller._sessions = {section.entry_key: section}
            controller._current_section_key = section.entry_key
            controller.project_model.replace([
                Project({"code": "demo", "name": "UI Test", "category": "Examples"}),
                Project({"code": "sandbox", "name": "Sandbox", "category": "Examples"}),
            ])
            controller.navigation_model.replace([
                NavigationEntry(key="demo/asset", title="Assets", glyph="link", group="",
                                command="", search_type="demo/asset"),
                NavigationEntry(key=section.entry_key, title="Collection", glyph="link", group="",
                                command="", search_type=section.search_type),
            ])
            model = controller._ensure_tab_workspace_model(tab)
            model.replace_nodes([WorkspaceNode(
                node_id="collection", node_type="sobject", title="Test Collection",
                search_key="demo/collection?project=demo&code=COLLECTION001",
                code="COLLECTION001", subtitle="DESC · demo/collection",
                preview_requested=True, card_preview_requested=True,
            )])
            controller._current_page_key = "demo/collection"
            controller._current_page_title = "Collection"
            controller._sync_section_model()
            controller._sync_search_tabs()
            controller._set_result_state(tab)
            controller.section_state_changed.emit()
            controller._server_state = "online"
            controller._authentication_required = False
            controller.server_state_changed.emit()
            window.setProperty("projectTitle", "UI Test")
            window.setProperty("pageKey", "demo/collection")
            window.setProperty("pageTitle", "Collection")
            QTest.mouseMove(window, QPoint(800, 800))
            save(window, "main")

            if configuration_only:
                editors = runtime[0].bundles[-1]
                configuration = editors.configuration
                rows = [dict(alias='base', title='Main repository', code='base', windowsPath='D:/private/assets', linuxPath='/private/assets', active=True,
                             isDefault=True, defaultEligible=True, status='available', statusText='Available', projectMapping='', selected=False, custom=False, color='')]
                with patch.object(controller, 'refresh_projects'), patch.object(editors.repository, 'begin_edit'):
                    editors.repository.model.replace(rows)
                    editors.repository._set_configuration_summary(True, rows)
                    configuration.begin_session()
                    controller.window_model.show_window('configuration')
                    settle()
                    native = next(w for w in app.allWindows() if w.isVisible() and w.title() == 'Configuration')
                    for width, height in ((1400, 940), (900, 620)):
                        native.resize(width, height)
                        for label, page_id in (('server','server'),('repositories','repository'),('projects','project'),('check-in-options','checkin_preferences'),
                                               ('global','global_preferences'),('appearance','appearance'),('cache','cache'),('tasks','tasks_preferences')):
                            configuration.select_page(page_id)
                            save(native, f'config-{label}-{width}')
                    controller.window_model.close_window('configuration')
                    controller.window_model.show_window('repository_editor')
                    settle()
                    editor = next(w for w in app.allWindows() if w.isVisible() and w.title() == 'Repository Editor')
                    for width, height in ((1400, 940), (900, 620)):
                        editor.resize(width,height)
                        save(editor,f'config-repository-editor-{width}')
                    controller.window_model.close_window('repository_editor')
                return

            if menus_only:
                expression = QQmlExpression(QQmlEngine.contextForObject(window), window,
                                           'dockMenu.openCenteredIn(contentItem)')
                expression.evaluate()
                if expression.hasError():
                    raise RuntimeError(expression.error().toString())
                settle()
                popup = next(w for w in app.allWindows() if w.isVisible()
                             and "Popup" in w.metaObject().className())
                save(popup, "dock-management-menu")
                QQmlExpression(QQmlEngine.contextForObject(window), window, 'dockMenu.close()').evaluate()
                controller.window_model.show_window('configuration')
                settle()
                native = next(w for w in app.allWindows() if w.isVisible() and w.title() == 'Configuration')
                native.resize(1440, 940)
                save(native, 'configuration')
                controller.window_model.close_window('configuration')
                return

            if progress_only:
                geometry = {}
                for width, loading in [(1440, True), (760, True), (759, True), (1440, False)]:
                    window.resize(width, 1000)
                    controller._set_loading(loading, 'Restoring search session: Collection')
                    name = 'system-progress-' + str(width) + ('-busy' if loading else '-idle')
                    save(window, name)
                    expression = QQmlExpression(QQmlEngine.contextForObject(window), window,
                        'JSON.stringify({width: notificationActivityButton.width, height: notificationActivityButton.height,'
                        'surfaceWidth: notificationActivitySurface.width, surfaceHeight: notificationActivitySurface.height,'
                        'compact: notificationActivityButton.compactProgress, duration: theme.motionMedium})')
                    result = expression.evaluate()[0]
                    if expression.hasError():
                        raise RuntimeError(expression.error().toString())
                    geometry[name] = json.loads(result)
                (OUTPUT / 'system-progress-geometry.json').write_text(json.dumps(geometry, indent=2) + '\n', encoding='utf-8')
                return

            if tabs_only:
                titles = ['Assets', 'Episode animation and lighting review', 'Short',
                          'Rendering and compositing for selected episode', 'Final delivery approval']
                section.tabs = [SearchTabSession(tab_id='capture-' + str(index), title=title,
                                                loaded=True, view_mode='continious', total=1)
                                for index, title in enumerate(titles)]
                section.current_tab_id = section.tabs[-1].tab_id
                controller._sync_search_tabs()
                controller.section_state_changed.emit()
                geometry = {}
                def items(parent):
                    for child in parent.childItems():
                        yield child
                        yield from items(child)
                settle()
                original_tabs = list(section.tabs)
                delegates = [next(item for item in items(window.contentItem())
                                  if item.objectName() == 'searchTabDelegate_' + tab.tab_id)
                             for tab in section.tabs]
                start = delegates[1].mapToItem(window.contentItem(), QPointF(delegates[1].width() / 2, delegates[1].height() / 2)).toPoint()
                finish = delegates[3].mapToItem(window.contentItem(), QPointF(delegates[3].width() / 2, delegates[3].height() / 2)).toPoint()
                QTest.mousePress(window, Qt.LeftButton, pos=start)
                QTest.mouseMove(window, start + QPoint(app.styleHints().startDragDistance() + 2, 0))
                QTest.mouseMove(window, finish)
                save(window, 'search-tabs-drag')
                geometry['drag'] = {'threshold': app.styleHints().startDragDistance(),
                                    'tabs': [{'title': item.property('title'), 'scale': item.scale(),
                                              'displacedX': item.property('displacedX')} for item in delegates]}
                if delegates[1].scale() < 1.029:
                    raise RuntimeError('Native tab drag did not activate')
                QTest.mouseRelease(window, Qt.LeftButton, pos=finish)
                section.tabs = original_tabs
                section.current_tab_id = original_tabs[-1].tab_id
                controller._sync_search_tabs()
                for width in [1440, 1000, 720, 360, 320]:
                    window.resize(width, 740 if width < 720 else 1000)
                    save(window, 'search-tabs-' + str(width))
                    geometry[width] = []
                    for tab in section.tabs:
                        delegate = next((item for item in items(window.contentItem())
                                         if item.objectName() == 'searchTabDelegate_' + tab.tab_id), None)
                        if delegate is None:
                            raise RuntimeError('Missing captured native tab: ' + tab.tab_id)
                        geometry[width].append({key: delegate.property(key) for key in
                                                ['title', 'current', 'width', 'naturalTabWidth', 'minimumTabWidth']})
                        label = next(item for item in items(delegate)
                                     if item.objectName() == 'workspaceTabSelectionLabel')
                        font = QFontInfo(label.property('font'))
                        geometry[width][-1]['font'] = {'family': font.family(), 'style': font.styleName(),
                                                     'weight': font.weight(), 'pixels': font.pixelSize()}
                original_sessions = controller._sessions
                controller._sessions = {key: SectionSession(entry_key=key, title=title, accent='#79a7bf',
                                                          search_type=key, tabs=[SearchTabSession(tab_id=key, title=title)], current_tab_id=key)
                                        for key, title in [('demo/assets', 'Assets'), ('demo/textures', 'Textures'), ('demo/episodes', 'Episodes')]}
                controller._sessions[section.entry_key] = section
                controller._sync_section_model()
                window.resize(1000, 740)
                settle()
                rail_tabs = sorted((item for item in items(window.contentItem()) if item.objectName() == 'sectionTabDelegate'),
                                   key=lambda item: item.property('index'))
                start = rail_tabs[0].mapToItem(window.contentItem(), QPointF(24, 21)).toPoint()
                finish = rail_tabs[2].mapToItem(window.contentItem(), QPointF(24, 21)).toPoint()
                QTest.mouseMove(window, start)
                save(window, 'section-rail-hover')
                QTest.mousePress(window, Qt.LeftButton, pos=start)
                QTest.mouseMove(window, start + QPoint(0, app.styleHints().startDragDistance() + 2))
                QTest.mouseMove(window, finish)
                save(window, 'section-rail-drag')
                if not rail_tabs[0].findChild(QObject, 'sectionTabDragHandler').property('active'):
                    raise RuntimeError('Native section drag did not activate')
                geometry['rail'] = {'target': rail_tabs[0].property('dragTargetIndex'),
                                    'tabs': [{'title': item.property('title'), 'width': item.width(), 'height': item.height(),
                                              'displacedY': item.property('displacedY')} for item in rail_tabs]}
                QTest.mouseRelease(window, Qt.LeftButton, pos=finish)
                controller._sessions = {key: SectionSession(entry_key=key, title=title, accent='#79a7bf', search_type=key,
                                                          tabs=[SearchTabSession(tab_id=key, title=title)], current_tab_id=key)
                                        for key, title in [('demo/long-' + str(index), 'Projects' if index == 0 else 'Section ' + str(index)) for index in range(23)]}
                controller._sessions[section.entry_key] = section
                controller._sync_section_model()
                QTest.mouseMove(window, QPoint(24, 72))
                save(window, 'section-rail-long')
                native_rail = next(item for item in items(window.contentItem()) if item.objectName() == 'sectionTabList')
                initial_y = native_rail.property('contentY')
                wheel = QWheelEvent(QPointF(24, 72), QPointF(window.mapToGlobal(QPoint(24, 72))), QPoint(0, -90),
                                    QPoint(0, -120), Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
                QApplication.sendEvent(window, wheel)
                save(window, 'section-rail-scrolled')
                geometry['railScroll'] = {'before': initial_y, 'after': native_rail.property('contentY'),
                                         'height': native_rail.height(), 'contentHeight': native_rail.property('contentHeight')}
                if abs(geometry['railScroll']['after'] - initial_y - 90) > 1:
                    raise RuntimeError('Native section rail wheel was not handled')
                controller._sessions = original_sessions
                controller._sync_section_model()
                QTest.mouseMove(window, QPoint(800, 600))
                settle()
                (OUTPUT / 'search-tabs-geometry.json').write_text(json.dumps(geometry, indent=2), encoding='utf-8')
                menu_titles = ['Assets', 'Short', titles[1]] + ['New Search ' + str(index) for index in range(4, 16)]
                section.tabs = [SearchTabSession(tab_id='menu-' + str(index), title=title, loaded=True)
                                for index, title in enumerate(menu_titles)]
                section.current_tab_id = section.tabs[-1].tab_id
                controller._sync_search_tabs()
                controller.section_state_changed.emit()
                settle()
                delegate = next(item for item in items(window.contentItem())
                                if item.objectName() == 'searchTabDelegate_menu-0')
                def menu_command(code):
                    expression = QQmlExpression(QQmlEngine.contextForObject(delegate), delegate, code)
                    expression.evaluate()
                    if expression.hasError():
                        raise RuntimeError(expression.error().toString())
                    settle()
                for width in [1000, 360, 320]:
                    window.resize(width, 1000 if width == 1000 else 740)
                    settle()
                    menu_command('(function() { tabOverflowMenu.actions = searchTabsView.allTabActions(); tabOverflowMenu.openBelow(tabOverflowButton) })()')
                    popup = next(w for w in app.allWindows() if w.isVisible() and 'Popup' in w.metaObject().className())
                    save(popup, 'search-tabs-menu-' + str(width))
                    menu_command('tabOverflowMenu.close()')
                section.closed_tabs = [SearchTabSession(tab_id='history-' + str(index), title=title)
                                       for index, title in enumerate([titles[4], titles[3]])]
                controller.search_tab_history_changed.emit()
                menu_command('tabHistoryMenu.openBelow(tabHistoryButton)')
                popup = next(w for w in app.allWindows() if w.isVisible() and 'Popup' in w.metaObject().className())
                save(popup, 'search-tab-history-320')
                return

            if toasts_only:
                notifications = next(bundle.notifications for bundle in runtime[0].bundles if hasattr(bundle, 'notifications'))
                notifications.clear()
                notifications._push('complete', 'Preferences saved')
                notifications._push('error', 'Unable to reach the server.', group='server')
                notifications._new_activity({'eventId': 'capture-activity', 'actorTitle': 'Artist',
                    'title': 'New activity', 'detail': 'Episode review updated', 'initials': 'AR'})
                for timer in notifications._timers.values():
                    timer.stop()
                def items(parent):
                    for child in parent.childItems():
                        yield child
                        yield from items(child)
                settle()
                native = next(w for w in app.allWindows() if w.isVisible()
                    and any(item.objectName() == 'mainNotificationStack' for item in items(w.contentItem())))
                save(native, 'notification-stack')
                geometry = {'width': native.width(), 'height': native.height(), 'cards': []}
                for card in [item for item in items(native.contentItem()) if item.objectName() == 'notificationCard']:
                    fields = {}
                    for item in items(card):
                        if item.objectName() in ['notificationAvatar', 'notificationMessage', 'notificationDetail', 'notificationSource']:
                            point = item.mapToItem(card, QPointF(0, 0))
                            fields[item.objectName()] = {'x': point.x(), 'y': point.y(), 'width': item.width(), 'height': item.height(), 'visible': item.isVisible()}
                    geometry['cards'].append({'kind': card.property('kind'), 'width': card.width(), 'height': card.height(), 'fields': fields})
                notifications.clear()
                notifications._upsert_progress('Loading data…')
                save(native, 'notification-progress')
                card = next(item for item in items(native.contentItem()) if item.objectName() == 'notificationCard')
                message = next(item for item in items(card) if item.objectName() == 'notificationMessage')
                geometry['progress'] = {'height': card.height(), 'messageWidth': message.width()}
                (OUTPUT / 'notification-stack-geometry.json').write_text(json.dumps(geometry, indent=2) + '\n', encoding='utf-8')
                notifications.clear()
                notifications._push('info', 'Artist', 'Please review the lighting.', action='messages', action_data='CAPTURE_CHAT',
                    source_type='message', source_title='Artist review', avatar_text='AR')
                for timer in notifications._timers.values():
                    timer.stop()
                save(native, 'notification-quick-reply')
                reply_geometry = {'width': native.width(), 'collapsedHeight': native.height()}
                notifications.begin_reply(0)
                settle()
                field = next(item for item in items(native.contentItem()) if item.objectName() == 'notificationReplyField')
                field.setProperty('text', 'Lighting approved')
                save(native, 'notification-quick-reply-edit')
                reply_geometry['editingHeight'] = native.height()
                reply_geometry['fields'] = {}
                card = next(item for item in items(native.contentItem()) if item.objectName() == 'notificationCard')
                for name in ('notificationReplyField', 'notificationSendReplyButton'):
                    item = next(item for item in items(card) if item.objectName() == name)
                    point = item.mapToItem(card, QPointF(0, 0))
                    reply_geometry['fields'][name] = {'x': point.x(), 'y': point.y(), 'width': item.width(), 'height': item.height()}
                notifications._quick_reply_failed(notifications.model._records[0]['notificationId'], 'Unable to send message')
                save(native, 'notification-quick-reply-error')
                reply_geometry['errorHeight'] = native.height()
                (OUTPUT / 'notification-quick-reply-geometry.json').write_text(json.dumps(reply_geometry, indent=2)+'\n', encoding='utf-8')
                notifications.clear()
                return

            if notifications_only:
                notifications = next(bundle.notifications for bundle in runtime[0].bundles if hasattr(bundle, 'notifications'))
                notifications.clear_history()
                notifications._push('complete', 'Preferences saved', group='client')
                notifications._push('complete', 'Check-in completed', 'preview.png', group='checkin')
                notifications._push('error', 'Unable to reach the server.', group='server')
                controller.window_model.show_window('notifications')
                settle()
                native = next(w for w in app.allWindows() if w.isVisible() and w.title() == 'Notifications')
                native.resize(806, 640)
                save(native, 'system-activity')
                metrics = []
                for width in (806, 760, 759, 684, 683, 360, 320):
                    native.resize(width, 740 if width < 400 else 640)
                    save(native, 'system-activity-' + str(width))
                    history = native.findChild(QObject, 'notificationHistoryList')
                    rows = [item for item in history.property('contentItem').childItems() if item.property('message')]
                    value = {'width': native.width(), 'height': native.height(), 'rows': [
                        {'width': item.width(), 'height': item.height()} for item in rows]}
                    for name in ('notificationsPanel', 'notificationsToolbar', 'notificationHistoryList', 'notificationHistoryFilters', 'notificationMessageText', 'notificationTimestampText'):
                        item = native.findChild(QObject, name)
                        if item is not None:
                            value[name] = {'width': item.width(), 'height': item.height()}
                    metrics.append(value)
                (OUTPUT / 'system-activity-geometry.json').write_text(json.dumps(metrics, indent=2) + '\n', encoding='utf-8')
                notifications.clear_history()
                save(native, 'system-activity-empty-320')
                return

            if connection_only:
                expression = QQmlExpression(QQmlEngine.contextForObject(window), window, 'connectionMenu.toggleBelow(connectionButton)')
                expression.evaluate()
                if expression.hasError():
                    raise RuntimeError(expression.error().toString())
                settle()
                popup = next(w for w in app.allWindows() if w.isVisible() and 'Popup' in w.metaObject().className())
                save(popup, 'connection-menu')
                return

            if editor_only:
                editor = runtime[0].script_editor
                with patch.object(editor, 'load'), patch.object(editor, 'refresh_scripts_tree'):
                    editor.create_new_script()
                    editor.update_editor_state('', 'editor_demo', 'hello', 'python', 'def hello(name):\n    # Demo server script\n    return {"greeting": name}\n\nRESULT = hello("World")\n', 'server')
                    editor._scripts = [dict(token='editor_demo/hello', folder='editor_demo', title='hello', language='python')]
                    editor._rebuild_tree()
                    editor._append_output('Server-Side execution time: 0.010s\n{\'greeting\': \'World\'}\n')
                    controller.window_model.show_window('script_editor')
                    settle()
                    native = next(w for w in app.allWindows() if w.isVisible() and w.title() == 'Script Editor')
                    native.resize(1100, 760)
                    save(native, 'script-editor')
                    source = native.findChild(QObject, 'scriptEditorSourceText')
                    if source is None:
                        raise RuntimeError('Current Handler Script Editor source was not found')
                    source.setProperty('text', '"""def fake(): ignored"""\nclass Worker:\n    def work(self, name="demo"):\n        """Run a job."""\n        return name\n    def next(self):\n        return self.wo')
                    source.forceActiveFocus()
                    QTest.keyClick(native, Qt.Key_End, Qt.ControlModifier)
                    QTest.keyClick(native, Qt.Key_Space, Qt.ControlModifier)
                    save(native, 'script-completion')
                    QTest.keyClick(native, Qt.Key_Escape)
                    QTest.keyClick(native, Qt.Key_O, Qt.ControlModifier | Qt.ShiftModifier)
                    save(native, 'script-outline')
                return

            if messages_only:
                from datetime import timezone, timedelta
                feed = next(bundle.messages for bundle in runtime[0].bundles if hasattr(bundle, 'messages'))
                stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                current = str(env_server.get_user() or 'admin')
                raw = [dict(code='CAPTURE1', __search_key__='sthpw/message_log?code=CAPTURE1', login='artist', timestamp=stamp,
                            message='The new collection is ready.\nPlease review the lighting.', __reactions__={'👍': [current]}),
                       dict(code='CAPTURE2', __search_key__='sthpw/message_log?code=CAPTURE2', login='artist', timestamp=stamp,
                            message='I have also updated the textures.'),
                       dict(code='CAPTURE3', __search_key__='sthpw/message_log?code=CAPTURE3', login=current, timestamp=stamp,
                            message='Thank you! I will take a look.', __delivery__={'status': 'read', 'recipientCount': 1, 'readCount': 1})]
                fixture = {'timestamp': stamp, 'messages': raw, 'current': current}
                (OUTPUT / 'messages-fixture.json').write_text(json.dumps(fixture, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
                with patch.object(feed, 'load'), patch.object(feed, 'refresh'), patch.object(feed, '_load_messages'), patch.object(feed, '_poll_active_conversation'), patch.object(feed, '_mark_read'):
                    if os.environ.get('STREAM_MESSAGES_NAVIGATION_CAPTURE'):
                        feed._users.replace([dict(login='artist', displayName='Artist', groups=[], presenceKnown=True, online=False,
                            lastSeen=(datetime.now(timezone.utc) - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ'))])
                    feed._initialized = True
                    feed._conversation_id = 'CAPTURE_CHAT'
                    feed._loaded_conversation_id = 'CAPTURE_CHAT'
                    feed._conversation_opened = True
                    rows = []
                    for code, title, recipients, personal in [('CAPTURE_NOTES', 'Personal Notes', [], True), ('CAPTURE_CHAT', 'Artist', ['artist'], False)]:
                        row = dict(conversationId=code, title=title, recipients=recipients, recipientNames=recipients, status='',
                            lastCleared=stamp, unread=0, mentionCount=0, selected=code=='CAPTURE_CHAT', lastMessage=raw[-1]['message'] if recipients else '',
                            lastTimestamp=stamp, lastSender=current, messageCount=3 if recipients else 0, attachmentCount=0,
                            createdBy=current, createdAt=stamp, isPersonalNotes=personal, canManage=True, canRename=not personal,
                            canDelete=not personal, canAddMembers=not personal, canClearPersonal=personal)
                        row.update(feed._conversation_profile(row)); rows.append(row)
                    feed.conversations.replace(rows)
                    feed.messages.replace(feed._group_message_records([feed._message_record(row, stamp, current) for row in raw]))
                    feed._sync_message_surfaces()
                    feed.stateChanged.emit()
                    controller.window_model.show_window('messages')
                    settle()
                    native = next(w for w in app.allWindows() if w.isVisible() and w.title() == 'Messages')
                    native.resize(1120, 760)
                    save(native, 'messages')
                    if os.environ.get('STREAM_MESSAGES_AUX_CAPTURE'):
                        pending = [native.contentItem()]
                        while pending:
                            host = pending.pop()
                            if host.metaObject().className().startswith('MessagesView'): break
                            pending.extend(host.childItems())
                        else: raise RuntimeError('MessagesView not found')
                        feed._pin_history = [dict(messageId=raw[0]['__search_key__'], pinnedBy='artist', pinnedAt=stamp, summary=raw[0]['message'])]
                        feed.stateChanged.emit()
                        cases = [
                            ('renameChatPopup', 'messages-rename', "chatTitleField.text = 'Lighting review'", True),
                            ('editMessageDialog', 'messages-edit', "root.pendingEditBody = 'Thank you! I will take a look.'", False),
                            ('forwardDialog', 'messages-forward', "messagesController.begin_forward('sthpw/message_log?code=CAPTURE3')", False),
                            ('editHistoryPopup', 'messages-edit-history', "root.selectedEditHistory = [{editedBy:'artist',editedAt:'" + stamp + "',body:'The new collection is ready.\\nPlease review the lighting.'}]", True),
                            ('pinHistoryPopup', 'messages-pin-history', '', True),
                        ]
                        for popup_id, name, setup, is_popup in cases:
                            if setup:
                                expression = QQmlExpression(QQmlEngine.contextForObject(host), host, setup)
                                expression.evaluate()
                                if expression.hasError(): raise RuntimeError(expression.error().toString())
                            expression = QQmlExpression(QQmlEngine.contextForObject(host), host,
                                popup_id + ('.openCenteredIn(Overlay.overlay)' if is_popup else '.open()'))
                            expression.evaluate()
                            if expression.hasError(): raise RuntimeError(expression.error().toString())
                            settle()
                            geometry = QQmlExpression(QQmlEngine.contextForObject(host), host,
                                'JSON.stringify({x:' + popup_id + '.x,y:' + popup_id + '.y,width:' + popup_id + '.width,height:' + popup_id + '.height,contentWidth:' + popup_id + '.contentItem.width,contentHeight:' + popup_id + '.contentItem.height})').evaluate()
                            if isinstance(geometry, tuple): geometry = geometry[0]
                            (OUTPUT / (name + '-geometry.json')).write_text(str(geometry) + '\n', encoding='utf-8')
                            if is_popup:
                                popup = next(w for w in app.allWindows() if w.isVisible() and 'Popup' in w.metaObject().className())
                                save(popup, name)
                            else:
                                box = json.loads(geometry)
                                picture = native.grabWindow().copy(*(round(box[key]) for key in ('x', 'y', 'width', 'height')))
                                if not picture.save(str(OUTPUT / (name + '.png'))): raise RuntimeError('Failed to capture ' + name)
                                print(name, picture.width(), picture.height(), flush=True)
                            QQmlExpression(QQmlEngine.contextForObject(host), host, popup_id + '.close()').evaluate()
                            settle()
                    if os.environ.get('STREAM_MESSAGES_PEOPLE_CAPTURE'):
                        users = next(bundle.users for bundle in runtime[0].bundles if hasattr(bundle, 'users'))
                        records = [dict(login=login, displayName=label, initials=initials, avatarUrl='', avatarColor=color,
                            groups=[group], primaryGroup=group, current=login == current, selected=False,
                            email='', presenceKnown=False, online=False, lastSeen='')
                            for login, label, initials, color, group in [(current, 'Administrator', 'A', '#467a6d', 'Admin'),
                                ('artist', 'Lighting Artist', 'LA', '#507eb0', 'Artists'), ('reviewer', 'Reviewer', 'R', '#9b7351', 'Supervisors')]]
                        with patch.object(users, 'refresh'), patch.object(users, '_rebuild'):
                            users.users.replace(records); feed._users.replace(records)
                            feed._can_create_group = True
                            users.stateChanged.emit(); feed.stateChanged.emit()
                            pending = [native.contentItem()]
                            while pending:
                                host = pending.pop()
                                if host.metaObject().className().startswith('MessagesView'): break
                                pending.extend(host.childItems())
                            else: raise RuntimeError('MessagesView not found')
                            for popup_id, name, setup in [('conversationPopup', 'messages-create-chat', "root.selectedRecipients = ['artist'];"),
                                                         ('addMembersPopup', 'messages-edit-members', ''), ('membersPopup', 'messages-members', '')]:
                                expression = QQmlExpression(QQmlEngine.contextForObject(host), host,
                                    popup_id + '.openCenteredIn(Overlay.overlay)')
                                expression.evaluate()
                                if expression.hasError(): raise RuntimeError(expression.error().toString())
                                settle()
                                if setup:
                                    expression = QQmlExpression(QQmlEngine.contextForObject(host), host, setup)
                                    expression.evaluate()
                                    if expression.hasError(): raise RuntimeError(expression.error().toString())
                                    settle()
                                popup = next(w for w in app.allWindows() if w.isVisible() and 'Popup' in w.metaObject().className())
                                geometry = QQmlExpression(QQmlEngine.contextForObject(host), host,
                                    "JSON.stringify({rootWidth:root.width,rootHeight:root.height,width:" + popup_id + ".width,height:" + popup_id + ".height,contentWidth:" + popup_id + ".contentItem.width,contentHeight:" + popup_id + ".contentItem.height})").evaluate()
                                if isinstance(geometry, tuple): geometry = geometry[0]
                                (OUTPUT / (name + '-geometry.json')).write_text(str(geometry) + '\n', encoding='utf-8')
                                save(popup, name)
                                QQmlExpression(QQmlEngine.contextForObject(host), host, popup_id + '.close()').evaluate()
                                settle()
                    if os.environ.get('STREAM_USER_PROFILE_CAPTURE'):
                        users = next(bundle.users for bundle in runtime[0].bundles if hasattr(bundle, 'users'))
                        with patch.object(users, 'refresh'), patch.object(users, '_rebuild'):
                            users._selected_login = 'artist'
                            users._directory_visible = False
                            users._profile = dict(login='artist', displayName='Lighting Artist', initials='LA', avatarUrl='', avatarColor='#507eb0', current=False,
                                email='artist@example.test', contact='+7 000 000', address='Studio', department='Lighting', project='demo', server='local',
                                firstName='Lighting', lastName='Artist', phoneNumber='+7 000 000', upn='', namespace='', status='', accountProject='', hourlyWage='',
                                groups=[dict(code='artists', label='Artists', accessLevel='medium')], roles=['Artist'], presenceKnown=True, online=True)
                            users._task_summary = dict(total=4, incomplete=3, overdue=1, dueThisWeek=2)
                            users._work_hour_summary = dict(loggedHours=10, approvedHours=8, pendingHours=2)
                            users._can_view_work_hours = True
                            users._task_status_summary = [dict(label='Pending', value='pending', count=3, color='#c8b55b'),dict(label='Complete',value='complete',count=1,color='#29a970')]
                            users._task_process_summary = [dict(label='Lighting',value='lighting',count=4,color='#507eb0')]
                            users.users.replace([dict(login='artist',displayName='Lighting Artist',initials='LA',email='artist@example.test',avatarUrl='',avatarColor='#507eb0',groups=['Artists'],primaryGroup='Artists',current=False,selected=True,presenceKnown=True,online=True,lastSeen=stamp)])
                            users.groups.replace([dict(code='artists',label='Artists',description='Artists',member=True,accessLevel='medium',projectCode='demo',isDefault=False)])
                            users.stateChanged.emit(); controller.window_model.show_window('user_profile'); settle()
                            profile_window = next(w for w in app.allWindows() if w.isVisible() and w.title() == 'User Profile')
                            profile_window.resize(960,740); save(profile_window,'user-profile')
                            pending = [profile_window.contentItem()]
                            while pending:
                                item = pending.pop()
                                if item.metaObject().className().startswith('UserProfileView'):
                                    expression = QQmlExpression(QQmlEngine.contextForObject(item), item, 'profileEditor.openForProfile()')
                                    expression.evaluate()
                                    if expression.hasError(): raise RuntimeError(expression.error().toString())
                                    save(profile_window, 'user-profile-editor')
                                    QQmlExpression(QQmlEngine.contextForObject(item), item, 'profileEditor.close()').evaluate()
                                    break
                                pending.extend(item.childItems())
                            users._directory_visible = True; users.stateChanged.emit(); profile_window.resize(1120,760); save(profile_window,'user-directory')
                            controller.window_model.close_window('user_profile')
                    if os.environ.get('STREAM_MESSAGES_BUBBLE_CAPTURE'):
                        pending = [native.contentItem()]
                        measured = []
                        composer = None
                        while pending:
                            item = pending.pop(); pending.extend(item.childItems())
                            name = item.objectName()
                            if name == 'messageComposerTextArea': composer = item
                            if name in ['messageTimelineBubble', 'messageMetadataRow', 'messageSenderLabel', 'messageTimeLabel', 'messageBodyText', 'messageComposerTextArea']:
                                record = dict(name=name, width=item.width(), height=item.height(), text=item.property('text'))
                                font = item.property('font')
                                if font:
                                    info = QFontInfo(font)
                                    record.update(fontPixels=info.pixelSize(), fontPoints=info.pointSizeF(), family=info.family())
                                measured.append(record)
                        (OUTPUT / 'messages-bubble-geometry.json').write_text(json.dumps(measured, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
                        feed.messages.replace(feed._group_message_records([feed._message_record(dict(row, message=text), stamp, current) for row, text in zip(raw, ['👍', '👍🏽 👨‍👩‍👧‍👦', '😀 😀 😀'])]))
                        save(native, 'messages-emoji-only')
                        feed.messages.replace(feed._group_message_records([feed._message_record(row, stamp, current) for row in raw]))
                        composer.setProperty('text', 'A multiline draft\nSecond line\nThird line')
                        save(native, 'messages-composer-multiline')
                        feed._sending = True; feed.stateChanged.emit()
                        save(native, 'messages-composer-sending')
                        feed._sending = False; feed.stateChanged.emit(); composer.setProperty('text', '')
                        quoted = [dict(row) for row in raw]
                        quoted[1]['__reply__'] = dict(messageId=raw[0]['__search_key__'], sender='artist', body=raw[0]['message'], available=True)
                        quoted[2]['__forwarded_from__'] = dict(messageId=raw[1]['__search_key__'], conversationId='CAPTURE_CHAT', sender='artist', body=raw[1]['message'], available=True, attachments=[])
                        feed.messages.replace(feed._group_message_records([feed._message_record(row, stamp, current) for row in quoted]))
                        feed._reply_target = dict(messageId=raw[0]['__search_key__'], senderDisplay='artist', body=raw[0]['message'])
                        feed.stateChanged.emit(); save(native, 'messages-references')
                        feed._reply_target = {}; feed.stateChanged.emit()
                        feed.messages.replace(feed._group_message_records([feed._message_record(row, stamp, current) for row in raw]))
                    if os.environ.get('STREAM_MESSAGES_NAVIGATION_CAPTURE'):
                        feed.conversations.replace([dict(row, unread=2, mentionCount=1) if index == 1 else row for index, row in enumerate(rows)])
                        feed.stateChanged.emit()
                        save(native, 'messages-counters-presence')
                        pending = [native.contentItem()]
                        named = {}
                        while pending:
                            item = pending.pop(); pending.extend(item.childItems())
                            if item.objectName(): named[item.objectName()] = item
                        original = list(feed.messages._records)
                        feed.messages.replace(feed._group_message_records([feed._message_record(dict(raw[0], code='NAV%s' % index,
                            __search_key__='sthpw/message_log?code=NAV%s' % index, message='History page %s' % index), stamp, current) for index in range(35)]))
                        settle(); named['messageTimelineList'].setProperty('contentY', 100)
                        save(native, 'messages-jump-latest')
                        feed.messages.replace(original)
                        source = named['messagesConversationListView']
                        point = source.mapToScene(QPointF(50, 100)).toPoint()
                        QTest.mouseClick(native, Qt.RightButton, Qt.NoModifier, point)
                        settle()
                        popup = next(w for w in app.allWindows() if w.isVisible() and 'Popup' in w.metaObject().className())
                        save(popup, 'messages-conversation-menu')
                        host = named['messageTimelineList'].property('host')
                        expression = QQmlExpression(QQmlEngine.contextForObject(host), host, 'chatActions.close()')
                        expression.evaluate()
                        if expression.hasError(): raise RuntimeError(expression.error().toString())
                        settle(); feed.dismiss_error()
                        feed.conversations.replace(rows)
                    if os.environ.get('STREAM_MESSAGES_HELP_CAPTURE'):
                        pending = [native.contentItem()]
                        refresh = None
                        while pending:
                            item = pending.pop()
                            if item.property('toolTip') == 'Refresh conversations and messages':
                                refresh = item; break
                            pending.extend(item.childItems())
                        if refresh is None:
                            raise RuntimeError('Messages refresh control was not found')
                        point = refresh.mapToScene(QPointF(refresh.width() / 2, refresh.height() / 2))
                        QTest.mouseMove(native, point.toPoint()); QTest.qWait(650)
                        save(native, 'messages-tooltip')
                        pending = [native.contentItem()]
                        tooltip_metrics = []
                        while pending:
                            item = pending.pop()
                            if item.property('text') == 'Refresh conversations and messages' and item.property('font'):
                                font = QFontInfo(item.property('font'))
                                tooltip_metrics.append(dict(width=item.width(), height=item.height(), fontSize=font.pixelSize(), family=font.family()))
                            pending.extend(item.childItems())
                        (OUTPUT / 'messages-tooltip-geometry.json').write_text(json.dumps(tooltip_metrics, indent=2) + '\n', encoding='utf-8')
                        QTest.mouseMove(native, QPoint(5, 5))
                        controller.window_model.open_help('communication')
                        settle()
                        help_window = next(w for w in app.allWindows() if w.isVisible() and w.title() == 'Help')
                        help_window.resize(1008, 760)
                        settle()
                        metrics = []
                        pending = [help_window.contentItem()]
                        while pending:
                            item = pending.pop(); pending.extend(item.childItems())
                            if item.objectName() in {'helpArticleBody', 'helpArticleSummaryText'}:
                                font = QFontInfo(item.property('font'))
                                metrics.append(dict(name=item.objectName(), fontSize=font.pixelSize(), family=font.family(), width=item.width(), height=item.height()))
                        (OUTPUT / 'help-geometry.json').write_text(json.dumps(metrics, indent=2)+'\n', encoding='utf-8')
                        save(help_window, 'messages-help')
                        help_window.close()
                    from PySide6.QtCore import QUrl
                    from PySide6.QtGui import QImage, QColor, QPainter
                    image = QImage(240, 135, QImage.Format.Format_RGB32)
                    image.fill(QColor('#354954'))
                    painter = QPainter(image)
                    painter.setPen(QColor('#d8e3e8'))
                    painter.drawText(image.rect(), Qt.AlignmentFlag.AlignCenter, 'Lighting review')
                    painter.end()
                    image_path = OUTPUT / 'messages-attachment.png'
                    image.save(str(image_path))
                    records = [feed._message_record(row, stamp, current) for row in raw]
                    records[-1]['attachments'] = [dict(token='CAPTURE_IMAGE', title='poster.png', size=image_path.stat().st_size,
                        extension='PNG', previewUrl=QUrl.fromLocalFile(str(image_path)).toString(), hasWebPreview=True, local=True, snapshotCode='CAPTURE_IMAGE'),
                        dict(token='CAPTURE_FILE', title='review.txt', size=62, extension='TXT', previewUrl='', hasWebPreview=False, local=False, snapshotCode='CAPTURE_FILE')]
                    records[-1]['attachmentCount'] = 2
                    feed.messages.replace(feed._group_message_records(records))
                    feed._sync_message_surfaces()
                    save(native, 'messages-attachments')
                    pending = [native.contentItem()]
                    while pending:
                        card = pending.pop()
                        if card.objectName() == 'messageAttachmentCard-CAPTURE_IMAGE':
                            break
                        pending.extend(card.childItems())
                    else:
                        raise RuntimeError('Attachment card not found')
                    expression = QQmlExpression(QQmlEngine.contextForObject(card), card,
                        "host.attachmentMenuToken = 'CAPTURE_IMAGE'; host.attachmentMenuLocal = false; "
                        "host.attachmentMenuImage = true; host.timelineAttachmentMenu.openAt(attachmentCard, 20, 20, false)")
                    expression.evaluate()
                    if expression.hasError():
                        raise RuntimeError(expression.error().toString())
                    settle()
                    popup = next(w for w in app.allWindows() if w.isVisible() and 'Popup' in w.metaObject().className())
                    save(popup, 'messages-attachment-menu')
                    host = QQmlExpression(QQmlEngine.contextForObject(card), card, 'host').evaluate()
                    if isinstance(host, tuple):
                        host = host[0]
                    expression = QQmlExpression(QQmlEngine.contextForObject(host), host, 'attachmentMenu.close(); filesPopup.open()')
                    expression.evaluate()
                    if expression.hasError():
                        raise RuntimeError(expression.error().toString())
                    settle()
                    popup = next(w for w in app.allWindows() if w.isVisible() and 'Popup' in w.metaObject().className())
                    save(popup, 'messages-chat-files')
                    expression = QQmlExpression(QQmlEngine.contextForObject(host), host,
                        "JSON.stringify({width: filesPopup.width, height: filesPopup.height, padding: filesPopup.padding, "
                        "listWidth: chatFilesList.width, listHeight: chatFilesList.height, spacing: chatFilesList.spacing})")
                    result = expression.evaluate()
                    if isinstance(result, tuple):
                        result = result[0]
                    (OUTPUT / 'messages-chat-files-geometry.json').write_text(result + '\n', encoding='utf-8')
                    if os.environ.get('STREAM_SKEY_CAPTURE') == '1':
                        fixture = json.loads((ROOT / '.screenshots/skey-preview-fixture.json').read_text(encoding='utf-8'))
                        expression = QQmlExpression(QQmlEngine.contextForObject(host), host, 'filesPopup.close()')
                        expression.evaluate()
                        with patch.object(feed, '_preview_records', return_value=[]):
                            rows = [feed._message_record(row, stamp, current) for row in fixture['messages']]
                        for descriptor in fixture['previews']:
                            if descriptor.get('kind') in ('note', 'message'):
                                descriptor.update(timePretty='Just now', timeSimple=descriptor.get('timestamp') or '')
                        rows[0]['skeyPreviews'] = fixture['previews']
                        feed.messages.replace(feed._group_message_records(rows))
                        feed.stateChanged.emit()
                        native.resize(1120, 1000)
                        settle()
                        pending = [native.contentItem()]
                        geometry = {}
                        expected = {}
                        for descriptor in fixture['previews']:
                            if descriptor.get('status') == 'ready':
                                expected.setdefault(descriptor['kind'], descriptor['searchKey'])
                        while pending:
                            item = pending.pop()
                            pending[0:0] = item.childItems()
                            if not item.metaObject().className().startswith('SKeyPreviewCard'):
                                continue
                            value = item.property('preview')
                            if hasattr(value, 'toVariant'):
                                value = value.toVariant()
                            if not isinstance(value, dict) or value.get('status') != 'ready':
                                continue
                            kind = value.get('kind', 'sobject')
                            labels = {chip.get('label') for chip in value.get('infoChips', [])}
                            name = 'snapshot-tiles-sequence' if kind == 'snapshot' and {'Tiles', 'Range'} <= labels else 'snapshot-tiles' if kind == 'snapshot' and 'Tiles' in labels else kind
                            if name in geometry or name == kind and value.get('searchKey') != expected.get(kind):
                                continue
                            geometry[name] = dict(width=item.width(), height=item.height())
                            grab = item.grabToImage()
                            settle()
                            if not grab or not grab.image().save(str(OUTPUT / ('skey-' + name + '.png'))):
                                raise RuntimeError('Failed to capture native sKey ' + name)
                            if kind == 'snapshot':
                                if name == 'snapshot':
                                    labels = []
                                    descendants = list(item.childItems())
                                    while descendants:
                                        child = descendants.pop()
                                        descendants.extend(child.childItems())
                                        if child.property('text') and child.property('font') is not None:
                                            font = QFontInfo(child.property('font'))
                                            color = child.property('color')
                                            labels.append(dict(text=child.property('text'), family=font.family(), pixelSize=font.pixelSize(), weight=font.weight(), color=color.name() if hasattr(color, 'name') else ''))
                                    (OUTPUT / 'snapshot-typography.json').write_text(json.dumps(labels, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                                item.setWidth(640)
                                settle()
                                grab = item.grabToImage()
                                settle()
                                if not grab or not grab.image().save(str(OUTPUT / ('skey-' + name + '-wide.png'))):
                                    raise RuntimeError('Failed to capture wide native snapshot')
                        if len(geometry) < 6:
                            raise RuntimeError('Native sKey cards did not render: ' + str(geometry))
                        (OUTPUT / 'skey-geometry.json').write_text(json.dumps(geometry, indent=2) + '\n', encoding='utf-8')
                return

            if activity_only:
                from thlib.ui.activity import activity_record
                feed = next(bundle.activity_feed for bundle in runtime[0].bundles if hasattr(bundle, 'activity_feed'))
                rich_links = os.environ.get('STREAM_RICH_LINKS_CAPTURE') == '1'
                fixture = json.loads((OUTPUT / ('activity-rich-links-fixture.json' if rich_links else 'activity-fixture.json')).read_text(encoding='utf-8'))
                with patch.object(feed, '_load'), patch.object(feed, 'ensure_calendar_counts'):
                    if rich_links:
                        feed.set_filter('notes')
                    feed._replace_records([activity_record(record) for record in fixture['records']])
                    feed._calendar_counts = fixture['counts']
                    feed._calendar_counts_loaded = feed._calendar_cache_complete = True
                    feed._busy = feed._has_more = False
                    controller.window_model.show_window('activity_feed')
                    settle()
                    native = next(w for w in app.allWindows() if w.isVisible() and w.title() == 'Activity Feed')
                    native.resize(922, 660)
                    if rich_links:
                        pending, expanded = [native.contentItem()], False
                        while pending:
                            card = pending.pop()
                            if card.objectName() == 'activityEventCard' and 'Rich links demonstration' in (card.property('detail') or ''):
                                expanded = card.setProperty('detailsExpanded', True)
                            pending.extend(card.childItems())
                        if not expanded:
                            raise RuntimeError('Native rich-link event was not expanded')
                        save(native, 'activity-rich-links')
                        return
                    save(native, 'activity-feed')
                    native.findChild(QObject, 'activityFeedCalendarButton').clicked.emit()
                    settle()
                    popup = next(w for w in app.allWindows() if w.isVisible() and w not in (window, native))
                    save(popup, 'activity-calendar')
                return

            if shelf_only:
                from thlib.ui.script_shelf import shelf_configuration_xml, SCRIPT_SHELF_GLOBAL_VIEW
                shelf = runtime[0].bundles[3].script_shelf
                shelf._project_code = 'demo'
                shelf._script_editor._scripts = [dict(folder='demo', title='hello', language='python')]
                shelf._sync_records([dict(code='SHELF001', search_type='SideBarWdg', category='script_shelf',
                    view=SCRIPT_SHELF_GLOBAL_VIEW, login='', title='Shared shelf',
                    config=shelf_configuration_xml([dict(buttonId='hello', title='Hello', description='Demo server script', iconName='play-arrow', script='demo/hello')], SCRIPT_SHELF_GLOBAL_VIEW, scope='global'))])
                shelf._editor_mode = 'shared'; shelf._shared_scope = 'global'
                shelf._editor_view = SCRIPT_SHELF_GLOBAL_VIEW
                shelf._load_editor()
                shelf._active_mode = 'shared'; shelf._refresh_effective()
                pending_items = [window.contentItem()]
                loader = None
                while pending_items:
                    item = pending_items.pop()
                    if item.objectName() == 'scriptShelfLoader':
                        loader = item; break
                    pending_items.extend(item.childItems())
                if loader is None or not loader.parentItem().setProperty('shelfOpen', True):
                    raise RuntimeError('Missing native search script shelf')
                save(window, 'script-shelf-bar')
                with patch.object(shelf, 'refresh'):
                    controller.window_model.show_window('script_shelf_editor')
                    settle()
                    native = next(w for w in app.allWindows() if w.isVisible() and w.title() == 'Script Shelf')
                    native.resize(864, 660)
                    save(native, 'script-shelf-editor')
                return

            if performance_only:
                monitor = controller.ui_performance
                monitor._samples.extend([
                    dict(sampleId=2, action='Load search results', window='TACTIC Stream', handlerMs=142.5,
                         frameMs=31.2, readyMs=165.0, details='{"requestAndSchemaMs": 130.0, "publicationMs": 12.5, "records": 20}', slow=True, status='Frame presented'),
                    dict(sampleId=1, action='Pointer press', window='TACTIC Stream', handlerMs=2.4,
                         frameMs=18.1, readyMs=-1.0, details='', slow=False, status='Frame presented'),
                ])
                controller.window_model.show_window('ui_performance')
                settle()
                native = next(w for w in app.allWindows() if w.isVisible() and w.title() == 'UI responsiveness')
                native.resize(1008, 660)
                settle()
                QTest.mouseClick(native, Qt.LeftButton, pos=QPoint(200, 180))
                save(native, 'ui-performance')
                return

            if debug_only:
                log = runtime[0].debug_log
                log.set_recording_levels(['ERROR', 'API'])
                log.clear()
                log.log('API', 'query', group='admin/rpc', source='TACTIC API',
                        module='api.js', function='query', duration=.125,
                        size_kb=4.5, details='{"request": {"method": "query"}}',
                        command='from urllib.request import urlopen\nprint("Example")')
                log.log('ERROR', 'Example request failed', group='admin/rpc',
                        source='TACTIC API', module='api.js', function='query',
                        stacktrace='ValueError: Example request failed')
                settle()
                controller.window_model.show_window('debug_log')
                settle()
                native = next(w for w in app.allWindows() if w.isVisible() and w.title() == 'Debug Log')
                native.resize(922, 680)
                log.select_entry(0)
                save(native, 'debug-log')
                return

            def evaluate(code):
                expression = QQmlExpression(QQmlEngine.contextForObject(window), window, code)
                expression.evaluate()
                if expression.hasError():
                    raise RuntimeError(expression.error().toString())

            QTest.mouseMove(window, QPoint(100, 200))
            evaluate("drawer.open()")
            save(window, "navigation")
            evaluate("drawer.close(); configMenu.toggleBelow(settingsButton)")
            settle()
            popup = next(w for w in app.allWindows() if w.isVisible()
                         and "Popup" in w.metaObject().className())
            save(popup, "main-menu")
            evaluate("configMenu.close(); projectChooser.toggle(projectButton)")
            settle()
            popup = next(w for w in app.allWindows() if w.isVisible()
                         and "Popup" in w.metaObject().className())
            save(popup, "project-chooser")
            evaluate("projectChooser.close()")
            for key in ("configuration",):
                controller.window_model.show_window(key)
                settle()
                title = "Configuration"
                candidates = [w for w in app.allWindows() if w.title() == title and w.isVisible()]
                if not candidates:
                    raise RuntimeError("Missing native window: " + key)
                candidates[-1].resize(1440, 940)
                save(candidates[-1], key)
                controller.window_model.close_window(key)
            for key in ("tasks", "notes"):
                if key == "tasks":
                    QQmlEngine.contextForObject(window).contextProperty(
                        "tasksController")._show_workspace_surface("browser")
                controller.dock_model.show_panel(key)
                save(window, "main-with-" + key)
        except Exception as error:
            failures.append(error)
        finally:
            app.quit()

    class CapturingApplication:
        instance = staticmethod(QApplication.instance)
        sendPostedEvents = staticmethod(QApplication.sendPostedEvents)

        def __new__(cls, *args):
            app = QApplication(*args)
            QTimer.singleShot(500, lambda: shoot(app))
            return app

    application.QApplication = CapturingApplication
    result = application.main()
    ticket.stop()
    filters.stop()
    if failures:
        raise failures[0]
    return result


def capture_tags():
    from tests.test_tag_cloud_qml import TagCloudQmlTests
    from PySide6.QtTest import QTest

    TagCloudQmlTests.setUpClass()
    sample = TagCloudQmlTests()
    sample.setUp()
    try:
        for width in (1440, 320):
            with sample.workspace.scene(width, animated=False, height=1000 if width > 320 else 740) as (window, view):
                popup, _ = sample.measure_open(window, view)
                QTest.qWait(150)
                window = sample.live_window(window)
                window.grabWindow().save(str(OUTPUT / ('tag-cloud-' + str(width) + '.png')))
                popup_window = sample.live_window(popup.property('contentItem').window())
                if popup_window != window:
                    popup_window.grabWindow().save(str(OUTPUT / ('tag-cloud-popup-' + str(width) + '.png')))
                sample.workspace.close_menu(popup)
                print('Handler tag cloud', width, flush=True)
    finally:
        sample.doCleanups()
        TagCloudQmlTests.tearDownClass()


def capture_suggestions():
    from tests.test_process_menu_latency import ProcessMenuLatencyTests
    from tests.test_tag_cloud_qml import TagCloudQmlTests
    from PySide6.QtCore import QObject
    from PySide6.QtQuick import QQuickItem
    from PySide6.QtTest import QTest

    ProcessMenuLatencyTests.setUpClass()
    sample = ProcessMenuLatencyTests()
    sample.setUp()
    try:
        for width in (1440, 320):
            with sample.scene(width, animated=False, height=1000 if width > 320 else 740) as (window, view):
                field = view.findChild(QQuickItem, 'tacticSearchInput')
                field.setProperty('text', 'blue'); field.forceActiveFocus()
                sample.controller.workspace_state.search_suggestion_model.replace([
                    dict(title='Blue', description='First description', keyword='blue', code='A', values={'name': 'Blue'}, selected=False),
                    dict(title='Blue Extra', description='Second description', keyword='', code='AB', values={'name': 'Blue Extra'}, selected=False),
                ])
                QTest.qWait(180)
                window = TagCloudQmlTests.live_window(sample, window)
                window.grabWindow().save(str(OUTPUT / ('search-suggestions-' + str(width) + '.png')))
                popup = view.findChild(QObject, 'tacticSearchSuggestionsPopup')
                popup_window = TagCloudQmlTests.live_window(sample, popup.property('contentItem').window())
                if popup_window != window:
                    popup_window.grabWindow().save(str(OUTPUT / ('search-suggestions-popup-' + str(width) + '.png')))
                popup.close()
                print('Handler search suggestions', width, flush=True)
    finally:
        sample.doCleanups()


def capture_administration():
    from tests.test_admin_naming import AdministrationNamingQmlTests
    from tests.test_editor_windows_qml import SidebarEditorQmlTests
    from tests.profile_ui_responsiveness import frame
    from PySide6.QtCore import QTimer, QEventLoop, QObject, QMetaObject
    AdministrationNamingQmlTests.setUpClass()
    naming_sample = AdministrationNamingQmlTests()
    naming_sample.setUp()
    sample = naming_sample.ui
    def settle():
        loop = QEventLoop(); QTimer.singleShot(180, loop.quit); loop.exec()
        frame(sample.window)
    def view(name):
        return next(item for item in SidebarEditorQmlTests.descendants(sample.window.contentItem())
                    if item.isVisible() and item.metaObject().className().startswith(name + '_'))
    def shot(name):
        settle()
        assert sample.window.grabWindow().save(str(OUTPUT / (name + '.png'))), name
        print(name, flush=True)
    try:
        fixture = sample.fixture
        fixture.app.removeTranslator(fixture.translator)
        fixture.engine.retranslate()
        # The renderer and controllers are real; only network catalog reads are fixtures.
        with patch.object(fixture.columns, 'load_definition_catalog'):
            fixture.columns._set_definition_catalog('demo', None, [dict(search_type='demo/asset', view='table', code='C1',
                config='<config><table><element name="code" title="Code"><display widget="text"/></element><element name="name" title="Name"><display widget="text"/></element></table></config>')], {'demo/asset': 'Assets'})
            view('AdminSearchTypesView').setProperty('page', 'entity_summary')
            users = sample.admin.usersEditor
            users._project = 'sthpw'
            users._loaded = users._can_write = True
            users._metadata = {'groups': {}, 'fields': list(users.FIELDS), 'groupCatalog': []}
            users._catalog = [{'identity': 'artist', 'document': {**dict.fromkeys(users.FIELDS, ''),
                'login': 'artist', 'code': 'artist', 'display_name': 'Artist', 'email': 'artist@example.test'}, 'snapshots': []}]
            users._catalog_loaded()
            users.select('artist')
            for width, height in ((900, 620), (1400, 940)):
                sample.window.resize(width, height)
                for section in ('types', 'schema', 'workflow', 'columns', 'sidebar', 'users', 'groups', 'rules'):
                    sample.click('adminSection_' + section)
                    frame(sample.window)
                    if fixture.warnings:
                        print(section, fixture.warnings)
                        fixture.warnings.clear()
                    sample.window.grabWindow().save(str(OUTPUT / f'{section}_{width}.png'))
            sample.click('adminSection_types')
            view('AdminSearchTypesView').setProperty('page', 'entity_details')
            sample.click('adminSearchTypeColor_choose')
            picker = sample.window.findChild(QObject, 'adminSearchTypeColor_dialog')
            picker.setProperty('hue', 7 / 12)
            picker.setProperty('saturation', 2 / 3)
            picker.setProperty('brightness', .6)
            shot('color-picker')
            QMetaObject.invokeMethod(picker, 'close')
            for page in ('details', 'fields', 'naming', 'workflows', 'summary'):
                view('AdminSearchTypesView').setProperty('page', 'entity_' + page)
                shot('types-' + ('workflow' if page == 'workflows' else page))
            sample.click('adminSection_schema')
            view('AdminGraphProperties').setProperty('page', 'add_node')
            shot('schema-add-node')
            sample.click('adminSection_users')
            for page in ('account', 'groups', 'profile'):
                view('AdminUserDetails').setProperty('page', page)
                shot('users-' + page)
            sample.click('adminSection_groups')
            view('SecurityGroupsView').setProperty('editorPage', 'details')
            shot('groups-details')
            sample.click('adminSection_columns')
            view('ColumnsEditorView').setProperty('catalogEditorMode', 'xml')
            shot('columns-xml')
            sample.click('adminSection_sidebar')
            for page in ('access', 'technical', 'item'):
                view('SidebarEntrySettings').setProperty('page', page)
                shot('sidebar-' + page)
            fixture.sidebar.set_mode('xml')
            shot('sidebar-xml')
            fixture.sidebar.set_mode('simple')
            sample.click('adminSection_workflow')
            view('AdminGraphView').setProperty('page', 'technical')
            shot('workflow-technical')
            view('AdminGraphView').setProperty('page', 'canvas')
            sample.admin.workflowEditor.select_node('review')
            shot('workflow-process')
            view('AdminGraphProperties').setProperty('page', 'add_node')
            shot('workflow-add-node')
            view('AdminGraphProperties').setProperty('page', 'selection')
            sample.admin.workflowEditor.select_node('')
            sample.click('adminToggleNavigation')
            shot('administration_collapsed')
    finally:
        naming_sample.doCleanups()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "script_editor.png").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="handler-reference-", dir=OUTPUT) as scratch:
        environment = os.environ.copy()
        environment.update({
            "PYTHONPATH": str(HANDLER), "PYTHONDONTWRITEBYTECODE": "1",
            "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software",
            "QSG_RENDER_LOOP": "basic", "QT_QPA_FONTDIR": "C:/Windows/Fonts",
            "TACTIC_QML_SMOKE_OFFLINE": "1", "TACTIC_QML_TEST_SETTINGS_DIR": scratch,
            "LOCALAPPDATA": scratch, "APPDATA": scratch,
            "XDG_CACHE_HOME": scratch + "/cache", "XDG_CONFIG_HOME": scratch + "/config",
            "ADMIN_SCREENSHOTS": str(OUTPUT), "EDITOR_WINDOW_SCREENSHOTS": str(OUTPUT),
        })
        commands = [
            [sys.executable, "-B", str(Path(__file__).resolve()), "--main"],
            [sys.executable, "-B", "-m", "unittest",
             "tests.test_administration_qml.AdministrationQmlTests.test_sections_create_real_views_without_warnings_at_narrow_and_wide_sizes",
             "tests.test_editor_windows_qml.EditorWindowQmlTests.test_preview_uses_real_object_views_and_stages_the_sidebar_default"],
        ]
        if '--tags-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--tags']]
        if '--administration-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--administration']]
        if '--search-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--search']]
        if '--debug-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--debug-only']]
        if '--performance-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--performance-only']]
        if '--shelf-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--shelf-only']]
        if '--editor-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--editor-only']]
        if '--activity-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--activity-only']]
        if '--connection-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--connection-only']]
        if '--notifications-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--notifications-only']]
        if '--tabs-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--tabs-only']]
        if '--progress-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--progress-only']]
        if '--toasts-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--toasts-only']]
        if '--messages-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--messages-only']]
        if '--menus-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--menus-only']]
        if '--configuration-only' in sys.argv:
            commands = [[sys.executable, '-B', str(Path(__file__).resolve()), '--main', '--configuration-only']]
        for command in commands:
            subprocess.run(command, cwd=ROOT, env=environment, check=True, timeout=90)
    metadata = {
        "captured_at": datetime.now().astimezone().isoformat(),
        "source": str(HANDLER), "mode": "Current Handler QML; offline synthetic test data",
        "command": "D:/Python314/python.exe -B tools/capture_handler_reference.py",
        "screenshots": [p.name for p in sorted(OUTPUT.glob("*.png"))],
    }
    (OUTPUT / "index.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Current Handler QML references</title>'
        '<style>body{background:#1c2022;color:#eee;font:16px Segoe UI;margin:24px}'
        'img{max-width:100%;height:auto}figure{margin:32px 0}a{color:#79a7bf}</style>'
        '<h1>Current Handler QML references</h1><p>' + escape(metadata["captured_at"])
        + ' · Offline synthetic test data; current source, default dark theme.</p>'
        + ''.join('<figure><figcaption>' + escape(name) + '</figcaption><a href="'
                  + escape(name) + '"><img loading="lazy" src="' + escape(name)
                  + '"></a></figure>' for name in metadata["screenshots"]), encoding="utf-8")
    print("Saved references:", OUTPUT)


if __name__ == "__main__":
    if '--administration' in sys.argv:
        sys.path.insert(0, str(HANDLER))
        sys.argv = [sys.argv[0]]
        capture_administration()
    elif '--search' in sys.argv:
        sys.path.insert(0, str(HANDLER))
        sys.argv = [sys.argv[0]]
        capture_suggestions()
    elif '--tags' in sys.argv:
        sys.path.insert(0, str(HANDLER))
        sys.argv = [sys.argv[0]]
        capture_tags()
    elif "--main" in sys.argv:
        sys.path.insert(0, str(HANDLER))
        debug_only = '--debug-only' in sys.argv
        performance_only = '--performance-only' in sys.argv
        shelf_only = '--shelf-only' in sys.argv
        editor_only = '--editor-only' in sys.argv
        activity_only = '--activity-only' in sys.argv
        connection_only = '--connection-only' in sys.argv
        notifications_only = '--notifications-only' in sys.argv
        tabs_only = '--tabs-only' in sys.argv
        progress_only = '--progress-only' in sys.argv
        toasts_only = '--toasts-only' in sys.argv
        messages_only = '--messages-only' in sys.argv
        menus_only = '--menus-only' in sys.argv
        configuration_only = '--configuration-only' in sys.argv
        sys.argv = [sys.argv[0]]
        raise SystemExit(capture_main(debug_only, performance_only, shelf_only, editor_only, activity_only, connection_only, notifications_only, tabs_only, progress_only, toasts_only, messages_only, menus_only, configuration_only))
    else:
        main()
