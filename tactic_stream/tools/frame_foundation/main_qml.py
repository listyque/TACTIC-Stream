"""Capture the real, offline Handler toolbar against its independent original."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
TH = Path('D:/code/th_codex')
OUT = Path(__file__).resolve().parent / 'output/main'
OUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--original', action='store_true')
args = parser.parse_args()
sys.path[:0] = [str(TH)]

with tempfile.TemporaryDirectory(dir=ROOT / '.tmp/frame-tests') as settings:
    os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QSG_RENDER_LOOP='basic',
                     QT_FONT_DPI='96', TACTIC_QML_SMOKE_OFFLINE='1',
                     QT_QPA_FONTDIR=str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'),
                     TACTIC_QML_TEST_SETTINGS_DIR=settings,
                     LOCALAPPDATA=settings, APPDATA=settings)
    from PySide6.QtCore import QEventLoop, QObject, QPoint, QPointF, QTimer, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtQml import QQmlEngine
    from PySide6.QtWidgets import QApplication
    from thlib.ui import application

    if args.original:
        reference = Path(__file__).resolve().parent / 'reference/main'
        archive = Path('D:/code/TACTIC_VUE/backups/2026-10-15_103116_before_shared_ui_foundation/TH.zip')
        with ZipFile(archive) as source:
            for name in source.namelist():
                if name.startswith('thlib/ui/qml/') and not name.endswith('/'):
                    target = reference / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read(name))
        application.UI_ROOT = reference / 'thlib/ui'
    failures = []

    def settle(app):
        loop = QEventLoop()
        QTimer.singleShot(120, loop.quit)
        loop.exec()
        app.processEvents()

    def grab(item):
        capture = item.grabToImage()
        assert capture, 'Toolbar must have a paintable area'
        loop = QEventLoop()
        ready = []
        capture.ready.connect(lambda: (ready.append(True), loop.quit()))
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        timer.start(3000)
        loop.exec()
        timer.stop()
        assert ready, 'Toolbar paint did not complete'
        return capture.image()

    def capture(app):
        print('Capturing native toolbar', flush=True)
        try:
            window = next(window for window in app.allWindows() if window.title().startswith('TACTIC-Handler'))
            top_bar = window.findChild(QObject, 'topAppBar')
            assert top_bar
            controller = QQmlEngine.contextForObject(window).contextProperty('appController')
            controller._server_state = 'online'
            controller.server_state_changed.emit()
            window.setProperty('projectTitle', 'Administration')
            user = QQmlEngine.contextForObject(window).contextProperty('userController')
            from thlib.ui.user_identity import user_avatar_color
            user._current_login = lambda: 'admin'
            user.users._records = [dict(login='admin',displayName='admin',initials='A',avatarColor=user_avatar_color('admin'))]
            user.stateChanged.emit()
            window.show()
            window.setPosition(0, 0)
            settle(app)
            rows = []
            keys = ['mainNavigation', 'mainProject', None, 'mainActivity', 'mainConnection',
                    'mainDcc', 'mainQueue', 'mainFeed', 'mainAppearance', 'mainSettings', 'mainAccount']
            for width in [640, 720, 900, 1280, 1920]:
                window.setWidth(width)
                window.setHeight(900)
                QTest.mouseMove(window, QPoint(0, 200))
                settle(app)
                content = top_bar.childItems()[1]
                if args.original:
                    assert len(content.childItems()) == len(keys)
                    controls = dict((key, item) for key, item in zip(keys, content.childItems()) if key)
                else:
                    controls = {item.property('frameId'): item for item in content.childItems()}
                geometry = {}
                for name, item in controls.items():
                    if not item.isVisible():
                        continue
                    point = item.mapToScene(QPointF(0, 0))
                    geometry[name] = dict(x=point.x(), y=point.y(), width=item.width(), height=item.height())
                assert geometry['mainNavigation']['x'] == 8
                assert geometry['mainAccount']['x'] + geometry['mainAccount']['width'] <= width
                label = 'original' if args.original else 'frame'
                filename = f'{label}-{width}.png'
                window.update()
                settle(app)
                image = grab(top_bar)
                assert len({image.pixelColor(x,y).name() for x in range(0,image.width(),4) for y in range(0,image.height(),4)})>8, 'Reject an unpainted screenshot'
                assert image.save(str(OUT / filename))
                rows.append(dict(width=width, geometry=geometry, screenshot=filename))
            settings_button = controls['mainSettings']
            point = settings_button.mapToScene(QPointF(settings_button.width()/2, settings_button.height()/2))
            QTest.mouseClick(window, Qt.LeftButton, pos=point.toPoint())
            settle(app)
            assert window.property('configMenuActions'), 'Settings click must reach the existing controller'
            QTest.keyClick(window, Qt.Key_Escape)
            (OUT / (label + '.json')).write_text(json.dumps(rows, indent=2), encoding='utf-8')
            print(f'{label}: real toolbar at {len(rows)} sizes; settings click passed', flush=True)
        except BaseException as error:
            print(repr(error), flush=True)
            failures.append(error)
        finally:
            app.quit()

    class CaptureApplication:
        instance = staticmethod(QApplication.instance)
        sendPostedEvents = staticmethod(QApplication.sendPostedEvents)

        def __new__(cls, *arguments):
            app = QApplication(*arguments)
            QTimer.singleShot(1000, lambda: capture(app))
            return app

    application.QApplication = CaptureApplication
    import faulthandler
    faulthandler.dump_traceback_later(20)
    status = application.main()
    faulthandler.cancel_dump_traceback_later()
    if failures:
        raise failures[0]
    raise SystemExit(status)
