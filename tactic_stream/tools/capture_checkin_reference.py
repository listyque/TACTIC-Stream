"""Capture current, unmodified Handler QML using its actual queue/plate controllers."""
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HANDLER = Path('D:/grav/Tactic Stream/TH')
OUTPUT = ROOT / '.screenshots/checkin-current'


def main():
    os.environ['QT_QPA_PLATFORM'] = 'windows'
    os.environ['QT_SCALE_FACTOR'] = '1'
    os.environ['QT_SCREEN_SCALE_FACTORS'] = '1'
    sys.path.insert(0,str(HANDLER))
    from tests.qt_application import gui_test_application
    from tests.test_commit_queue_layout import _ScreenshotController, _NamingEditorController, _WindowModel
    from tests.test_drop_plate import _Templates, _Queue
    from thlib.ui.commit_queue import CommitQueueController
    from thlib.ui.drop_plate import DropPlateController
    from thlib.ui.matching_templates import MatchingTemplatesController
    from thlib.ui.icon_font import qml_icon_bindings
    from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtTest import QTest

    class Checkin(QObject):
        stateChanged = Signal()
        @Property(bool,notify=stateChanged)
        def hasObject(self): return True
        @Property(bool,notify=stateChanged)
        def actionAvailable(self): return True
        @Property(bool,notify=stateChanged)
        def keepFileName(self): return False
        @Property('QVariantMap',notify=stateChanged)
        def currentObject(self): return dict(title='Queue asset',code='QUEUE001')
        @Slot(bool)
        def set_keep_file_name(self,value): pass

    app = gui_test_application(); engine = QQmlEngine(); window = None
    sources = OUTPUT / 'sources'; sources.mkdir(parents=True,exist_ok=True)
    data = json.loads((OUTPUT / 'projection.json').read_text(encoding='utf8'))
    for file in data['source']:
        (sources / file['name']).write_bytes(b'x' * file['size'])
    with patch('thlib.ui.commit_queue.env_read_config',side_effect=lambda **kw: [] if kw.get('filename') == 'pending' else {}), patch('thlib.ui.commit_queue.env_write_config'), patch('thlib.ui.drop_plate.env_read_config',return_value={}), patch('thlib.ui.drop_plate.env_write_config'):
        queue = CommitQueueController()
        with patch('thlib.ui.matching_templates.env_read_config',return_value={}):
            templates = MatchingTemplatesController()
        checkin = Checkin()
        plate = DropPlateController(SimpleNamespace(),checkin,_Queue(),_Templates())
        result = plate._collect_groups([(sources / file['name']).as_posix() for file in data['source']],False,
                                      ('$FILENAME','$FILENAME.$EXT','$FILENAME.$FRAME.$EXT','$FILENAME_$UDIM.$EXT'),3)
        plate._groups_ready(result); plate._group_checkin = True
        assert plate.count == 2, (result.get('errors'),plate.error)
        operation = dict(searchKey=data['owner'],process='publish',context='publish/browser',repository='default',mode='upload',
                         files=[dict(path=(sources / file['name']).as_posix(),type='main') for file in data['source']],filesDict=[],
                         description='Prepared in Commit Queue',updateVersionless=True,keepFileName=False,generatePreviews=True)
        queue.add_prepared(operation,'Queue asset'); queue._advanced_options_expanded = True
        queue.set_auto_clean(False)
        queue.stateChanged.emit()
    context = engine.rootContext()
    for name,value in dict(commitQueueController=queue,commitQueueModel=queue.model,dropPlateController=plate,dropPlateModel=plate.model,
                           checkinOutController=checkin,matchingTemplatesController=templates,matchingTemplatesModel=templates.model,screenshotController=_ScreenshotController(engine),namingEditorController=_NamingEditorController(engine),windowModel=_WindowModel(engine)).items():
        context.setContextProperty(name,value)
    for name,value in qml_icon_bindings(HANDLER,engine).items(): context.setContextProperty(name,value)
    try:
        captures = {}
        for name,component_name,extent in [('drop-plate','DropPlateView','plate'),('queue-basic','CommitQueueView','queue'),('queue-prepared','CommitQueueView','queue'),('matching-templates','MatchingTemplatesView','templates')]:
            queue._advanced_options_expanded = name == 'queue-prepared'
            queue.stateChanged.emit()
            dimensions = data['dimensions'][extent]; width,height = round(dimensions['width']),round(dimensions['height'])
            qml = '''import QtQuick
import QtQuick.Controls
import "%s" as Handler
ApplicationWindow {
    width:%d; height:%d; visible:false
    Handler.Theme { id:theme; dark:true }
    Handler.%s { anchors.fill:parent; theme:theme %s }
}''' % ((HANDLER / 'thlib/ui/qml').as_uri(),width,height,component_name,'; windowId:"checkin-reference"' if extent == 'templates' else '')
            component = QQmlComponent(engine); component.setData(qml.encode(),QUrl.fromLocalFile(str(ROOT / 'tools/checkin-reference.qml')))
            window = component.create()
            if window is None: raise RuntimeError('\n'.join(error.toString() for error in component.errors()))
            window.setScreen(app.primaryScreen()); window.show()
            if extent == 'templates':
                templates.select_row(8); templates.update_selected('enabled',True)
                templates.update_selected('process','publish'); templates.update_selected('context','publish/browser')
                templates.test_pattern('diffuse_color.txt')
            QTest.qWait(500); app.processEvents()
            capture = window.grabWindow()
            ratio = window.devicePixelRatio()
            assert abs(capture.width() - width * ratio) <= 1 and abs(capture.height() - height * ratio) <= 1
            captures[name] = dict(logicalWidth=width,logicalHeight=height,devicePixelRatio=ratio,pixelWidth=capture.width(),pixelHeight=capture.height())
            if not capture.save(str(OUTPUT / ('handler-' + name + '.png'))): raise RuntimeError('Empty QML image')
            window.close(); window.deleteLater(); window = None; app.processEvents()
        files = ['thlib/ui/qml/DropPlateView.qml','thlib/ui/qml/CommitQueueView.qml','thlib/ui/qml/CommitQueueOperationSummary.qml','thlib/ui/qml/CommitQueueActionMenus.qml','thlib/ui/qml/MatchingTemplatesView.qml','thlib/ui/drop_plate.py','thlib/ui/commit_queue.py','thlib/ui/matching_templates.py','thlib/global_functions.py','thlib/tactic_query.py']
        (OUTPUT / 'source-manifest.json').write_text(json.dumps({ name:hashlib.sha256((HANDLER / name).read_bytes()).hexdigest() for name in files },indent=2),encoding='utf8')
        (OUTPUT / 'capture-geometry.json').write_text(json.dumps(captures,indent=2),encoding='utf8')
    finally:
        if window: window.close()
        with patch('thlib.ui.commit_queue.env_write_config'):
            queue.shutdown()
        app.processEvents()


if __name__ == '__main__': main()
