"""Trusted image viewer: all agent code and replayed input execute in OCI containers only."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from tactic_stream.automation_trial import AutomationTrials, digest


def reviewed_drafts(directory, image):
    content = (directory/'03-drafts-for-review.json').read_bytes()
    if hashlib.sha256(content).hexdigest() != (directory/'review-approved.txt').read_text(encoding='utf-8').strip():
        raise ValueError('The reviewed source changed')
    receipts = [json.loads(path.read_text(encoding='utf-8')) for path in (directory/'trials').glob('*.json')]
    drafts = []
    for row in json.loads(content):
        document = json.loads(row['document'])
        if not any(record.get('status') == 'passed' and record['image'] == image and
                   record['document_hash'] == digest(document) for record in receipts):
            raise ValueError('This exact source has no successful isolated test')
        drafts.append(dict(draft_id=row['code'], revision=digest(document), document=document,
                           dependency_revision='user-playground'))
    return drafts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result-dir', type=Path, required=True)
    parser.add_argument('--trial-image', required=True)
    args = parser.parse_args()
    directory = args.result_dir.resolve()
    drafts = reviewed_drafts(directory, args.trial_image)
    runner = AutomationTrials(args.trial_image, directory/'user-trials', ['user-playground'])
    from PySide6.QtCore import QThread, Qt, Signal
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QPlainTextEdit

    class Run(QThread):
        ready = Signal(object)

        def __init__(self, draft, case, parent):
            super().__init__(parent)
            self.draft, self.case = draft, case

        def run(self):
            try:
                result = runner.run(str(uuid4()), self.draft, self.case, 'agentfilm')
            except Exception as error:
                result = dict(status='failed', error=str(error))
            self.ready.emit(result)

    class Canvas(QLabel):
        action = Signal(object)

        def mousePressEvent(self, event):
            if self.pixmap() and not self.pixmap().isNull():
                self.setFocus()
                self.action.emit(dict(kind='point', x=int(event.position().x()), y=int(event.position().y())))

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Backspace:
                self.action.emit(dict(kind='backspace'))
            elif event.text() and not event.modifiers() & Qt.ControlModifier:
                self.action.emit(dict(kind='text', text=event.text()))

    class Viewer(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('Результат агента — изолированный тест')
            self.actions = []
            self.worker = None
            self.shelf = next(item for item in drafts if item['document']['kind'] == 'shelf')
            layout = QVBoxLayout(self)
            self.status = QLabel('Код выполняется только в контейнере. Каждый ввод повторяет сценарий с начала.')
            layout.addWidget(self.status)
            buttons = QHBoxLayout()
            layout.addLayout(buttons)
            for label, callback in [('Окно / сброс', self.reset), ('Чекин: разрешить', lambda: self.hook('allow')),
                                    ('Чекин: отклонить', lambda: self.hook('reject')), ('After', lambda: self.hook('after'))]:
                button = QPushButton(label)
                button.clicked.connect(callback)
                buttons.addWidget(button)
            self.canvas = Canvas('Нажми «Окно / сброс», затем проверяй элементы на изображении кликами.')
            self.canvas.setFocusPolicy(Qt.StrongFocus)
            self.canvas.action.connect(self.input)
            layout.addWidget(self.canvas)
            entry = QHBoxLayout()
            self.text = QLineEdit()
            self.text.setPlaceholderText('Текст для выбранного поля внутри окна')
            send = QPushButton('Ввести')
            send.clicked.connect(lambda: self.input(dict(kind='text', text=self.text.text())))
            entry.addWidget(self.text)
            entry.addWidget(send)
            layout.addLayout(entry)
            self.log = QPlainTextEdit()
            self.log.setReadOnly(True)
            self.log.setMaximumHeight(160)
            layout.addWidget(self.log)

        def reset(self):
            if self.busy():
                return
            self.actions = []
            self.start(self.shelf, dict(expect='modal'))

        def busy(self):
            return self.worker is not None

        def input(self, action):
            if self.busy():
                return
            if len(self.actions) >= 16:
                self.status.setText('Достигнут предел 16 действий. Нажми «Окно / сброс».')
                return
            self.actions.append(action)
            self.start(self.shelf, dict(expect='modal', actions=list(self.actions)))

        def hook(self, expected):
            if self.busy():
                return
            phase = 'after' if expected == 'after' else 'before'
            draft = next(item for item in drafts if item['document']['kind'] == 'hook' and item['document']['phase'] == phase)
            name = 'blocked.bin' if expected == 'reject' else 'accepted.bin'
            case = dict(expect='reject' if expected == 'reject' else 'allow', files=[dict(name=name, content='Owned test file')])
            if phase == 'after':
                case['artifacts'] = [dict(name='files/after.txt', contains='sthpw/snapshot')]
            self.start(draft, case)

        def start(self, draft, case):
            self.status.setText('Идёт изолированный прогон…')
            self.canvas.setEnabled(False)
            self.worker = Run(draft, case, self)
            self.worker.ready.connect(self.result)
            self.worker.finished.connect(self.finished)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker.start()

        def finished(self):
            self.worker = None
            self.canvas.setEnabled(True)

        def result(self, record):
            self.status.setText('Проверка: ' + record['status'] + '. Клики и ввод исполняются в контейнере.')
            result = record.get('result', {})
            self.log.setPlainText(json.dumps(result.get('observations', []), ensure_ascii=False, indent=2)
                + '\n' + record.get('error', '') + '\n' + result.get('log', '')[-12000:])
            encoded = result.get('screenshot')
            if encoded:
                try:
                    data = base64.b64decode(encoded, validate=True)
                    if len(data) > 2*1024*1024 or not data.startswith(b'\x89PNG\r\n\x1a\n'):
                        raise ValueError('Invalid preview image')
                    width, height = struct.unpack('>II', data[16:24])
                    if not width or not height or width*height > 2000000:
                        raise ValueError('Preview image is too large')
                    image = QImage.fromData(data, 'PNG')
                    if image.isNull():
                        raise ValueError('Preview image could not be decoded')
                    self.canvas.setPixmap(QPixmap.fromImage(image))
                    self.canvas.setFixedSize(width, height)
                    self.canvas.setFocus()
                except (ValueError, TypeError, struct.error) as error:
                    self.status.setText('Ошибка: снимок из контейнера не прошёл проверку.')
                    self.log.appendPlainText(str(error))
                    self.canvas.clear()

        def closeEvent(self, event):
            if self.busy():
                self.status.setText('Дождись завершения прогона перед закрытием — до 90 секунд.')
                event.ignore()
            else:
                event.accept()

    app = QApplication([])
    window = Viewer()
    window.show()
    app.exec()


if __name__ == '__main__':
    main()
