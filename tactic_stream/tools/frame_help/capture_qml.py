"""Capture original Handler and shared Help with identical shipped article data."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TH = Path('D:/code/th_codex')
OUT = Path(__file__).resolve().parent / 'output'
OUT.mkdir(parents=True, exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QSG_RENDER_LOOP='basic')
sys.path[:0] = [str(TH), str(ROOT / 'tools/frame_admin')]
from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl, QCoreApplication, QEvent, QPointF
from PySide6.QtQml import QQmlEngine, QQmlComponent
from PySide6.QtGui import QTextTable
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.help import HelpController
from thlib.ui.localization import CatalogTranslator
from native_capture import snapshot, source_hashes, assert_icons, controls


class Localization(QObject):
    languageChanged = Signal()

    def __init__(self, language):
        super().__init__()
        self.language = language

    @Property(str, notify=languageChanged)
    def current_language(self):
        return self.language


class Windows(QObject):
    helpRequested = Signal(str)
    helpTopicChanged = Signal()

    @Property(str, notify=helpTopicChanged)
    def helpTopic(self):
        return 'windows'

    @Slot(str)
    def close_window(self, name):
        pass


def main():
    app = gui_test_application()
    icons = qml_icon_bindings(TH, app)
    rows = []
    original_root = ROOT / 'tools/frame_foundation/reference/thlib/ui/qml'
    assert (original_root / 'HelpView.qml').is_file(), 'Extract the saved original first'
    for original in (True, False):
        qml = original_root if original else TH / 'thlib/ui/qml'
        for style in ('md3', 'material5', 'fluent'):
            for dark in (True, False):
                for language in ('en', 'ru'):
                    for width in (1100, 320):
                        translator = CatalogTranslator(TH / 'thlib/ui/translations/ru.json') if language == 'ru' else None
                        if translator:
                            app.installTranslator(translator)
                        engine = QQmlEngine()
                        warnings = []
                        engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
                        localization, windows = Localization(language), Windows()
                        help_controller = HelpController(TH / 'thlib/ui/help_articles', localization)
                        for name, value in dict(icons, helpController=help_controller, windowModel=windows, localizationController=localization).items():
                            engine.rootContext().setContextProperty(name, value)
                        source = ('import QtQuick\nimport QtQuick.Controls\nimport "' + qml.as_uri() + '" as TH\n'
                                  'ApplicationWindow { visible:true; width:' + str(width) + ';height:740;'
                                  'TH.Theme {id:theme; styleName:"' + style + '";dark:' + str(dark).lower() + ';'
                                  'clickAnimationsEnabled:false;hoverAnimationsEnabled:false;fadeAnimationsEnabled:false;popupAnimationsEnabled:false}'
                                  'TH.HelpView {theme:theme;anchors.fill:parent} }')
                        component = QQmlComponent(engine)
                        component.setData(source.encode(), QUrl())
                        assert component.isReady(), [error.toString() for error in component.errors()]
                        window = component.create()
                        assert window
                        try:
                            for _ in range(3):
                                frame(window)
                            original_diagnostics = []
                            if original:
                                try:
                                    assert_icons(window)
                                except AssertionError as error:
                                    original_diagnostics.append(str(error))
                            result = snapshot(window, check_icons=not original)
                            body = controls(window).get('documentBody')
                            if body is not None:
                                text_document = body.property('textDocument')
                                document = text_document.textDocument()
                                origin = body.mapToScene(QPointF())
                                tables = []
                                for child in document.rootFrame().childFrames():
                                    if isinstance(child, QTextTable):
                                        box = document.documentLayout().frameBoundingRect(child)
                                        tables.append(dict(x=origin.x()+box.x(),y=origin.y()+box.y(),width=box.width(),height=box.height()))
                                result['documentTables'] = tables
                                result['plainText'] = document.toPlainText()
                                del document, text_document
                            filename = f'{"original" if original else "native"}-{style}-{int(dark)}-{language}-{width}.png'
                            assert window.grabWindow().save(str(OUT / filename))
                            assert not warnings, warnings
                            rows.append(dict(original=original, originalDiagnostics=original_diagnostics, style=style, dark=dark, language=language, width=width, image=filename, articleTitle=help_controller.article["title"], **result))
                        finally:
                            if translator:
                                app.removeTranslator(translator)
                            window.close()
                            window.deleteLater()
                            engine.deleteLater()
                            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    native_files = ['thlib/ui/qml/features/support/help/HelpView.qml', 'thlib/ui/qml/controls/DocumentPane.qml', 'thlib/ui/help.py']
    native_files += [path.relative_to(TH).as_posix() for path in (TH / "thlib/ui/help_articles").glob("*.md")]
    shared, native = source_hashes(ROOT, TH, native_files)
    originals = {str(path.relative_to(original_root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in original_root.rglob('*.qml')}
    (OUT / 'native.json').write_text(json.dumps(dict(captures=rows, sha256=shared, nativeSources=native, originalSources=originals), indent=2), encoding='utf-8')
    print(f'Help: {len(rows)} original/native captures; 3 styles, light/dark, EN/RU, desktop/phone; zero QML warnings.')


if __name__ == '__main__':
    main()
