"""Drive the fixed host viewer; generated Python still runs only in OCI trials."""
import argparse
import importlib.util
import os
from pathlib import Path
import sys
import time

os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
parser = argparse.ArgumentParser()
parser.add_argument('--result-dir', type=Path, required=True)
parser.add_argument('--trial-image', required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
ROOT = Path(__file__).resolve().parents[2]
sys.argv = ['try_agent_automation.py', '--result-dir', str(args.result_dir), '--trial-image', args.trial_image]
from PySide6 import QtWidgets
from PySide6.QtCore import QTimer, QPoint, Qt
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtTest import QTest
OriginalApplication = QtWidgets.QApplication
outcome = []


def automate(app):
    window = next(widget for widget in app.topLevelWidgets() if widget.windowTitle().startswith('Результат агента'))
    def wait():
        deadline = time.monotonic()+110
        while window.busy() and time.monotonic() < deadline:
            QTest.qWait(20)
        assert not window.busy(), 'Viewer did not finish'
        assert 'passed' in window.status.text(), window.log.toPlainText()
        QTest.qWait(50)
    def button(text):
        return next(item for item in window.findChildren(QtWidgets.QPushButton) if item.text() == text)
    try:
        QTest.mouseClick(button('Окно / сброс'), Qt.LeftButton)
        wait()
        initial = window.canvas.pixmap().toImage()
        QTest.mouseClick(window.canvas, Qt.LeftButton, pos=QPoint(554, 550))
        wait()
        preview = window.canvas.pixmap().toImage()
        assert preview != initial, 'Native Preview did not change the image'
        QTest.mouseClick(window.canvas, Qt.LeftButton, pos=QPoint(70, 550))
        wait()
        assert window.canvas.pixmap().toImage() != preview, 'Native Clear did not change the image'
        QTest.mouseClick(button('Окно / сброс'), Qt.LeftButton)
        wait()
        QTest.mouseClick(window.canvas, Qt.LeftButton, pos=QPoint(100, 70))
        wait()
        window.text.setText('XYZ')
        QTest.mouseClick(button('Ввести'), Qt.LeftButton)
        wait()
        assert window.grab().save(str(args.output/'viewer.png'))
        for text in ('Чекин: разрешить', 'Чекин: отклонить', 'After'):
            QTest.mouseClick(button(text), Qt.LeftButton)
            wait()
        outcome.append(True)
        print('Actual viewer: Preview/Clear clicks, text input, allow/reject/After, worker release and close passed', flush=True)
    except BaseException as error:
        print(type(error).__name__, str(error), flush=True)
        outcome.append(False)
    finally:
        window.close()
        app.quit()


class Application(OriginalApplication):
    def __init__(self, values):
        super().__init__(values)
        if os.name == 'nt':
            QFontDatabase.addApplicationFont(str(Path(os.environ['WINDIR'])/'Fonts/segoeui.ttf'))
            self.setFont(QFont('Segoe UI'))
        QTimer.singleShot(100, lambda: automate(self))


QtWidgets.QApplication = Application
spec = importlib.util.spec_from_file_location('trial_viewer', ROOT/'tools/try_agent_automation.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.main()
raise SystemExit(not outcome or not all(outcome))
