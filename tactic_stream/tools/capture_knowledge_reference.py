"""Fresh Handler QML renders using the web test's native Knowledge Base fixture."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
HANDLER = Path('D:/code/th_codex')
OUTPUT = ROOT / '.screenshots/knowledge-current'


def main():
    sys.path.insert(0, str(HANDLER))
    from tests.test_knowledge_base import _KnowledgeStub, _AttachmentStub, _PreviewStub
    from tests.qt_application import gui_test_application
    from PySide6.QtCore import Property, QUrl, QObject, QMetaObject, Q_ARG
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtTest import QTest
    from thlib.ui.icon_font import qml_icon_bindings
    from thlib.ui.workspace_models.records import RecordListModel

    class Controller(_KnowledgeStub):
        @Property(str, notify=_KnowledgeStub.stateChanged)
        def projectCode(self): return 'one'
        @Property(int, notify=_KnowledgeStub.stateChanged)
        def readingMinutes(self): return 1
        @Property(int, notify=_KnowledgeStub.stateChanged)
        def viewerReadingMinutes(self): return 1

    app = gui_test_application()
    engine = QQmlEngine()
    controller = Controller()
    upload = _AttachmentStub()
    preview = _PreviewStub()
    data = json.loads((OUTPUT / 'projection.json').read_text(encoding='utf8'))
    roles = ('identity', 'title', 'description', 'excerpt', 'kind', 'depth', 'hasChildren', 'expanded', 'draft', 'localDraft')
    navigation = RecordListModel(roles)
    staging = RecordListModel(('token', 'title', 'extension', 'sizeText', 'previewUrl', 'isImage', 'error'))
    for name, value in dict(knowledgeController=controller, knowledgeNavigationModel=navigation,
                            knowledgeAttachments=upload, knowledgeAttachmentDraftModel=staging,
                            skeyPreviewResolver=preview, knowledgeRichText=controller.richTextDocument).items():
        engine.rootContext().setContextProperty(name, value)
    for name, value in qml_icon_bindings(HANDLER, engine).items():
        engine.rootContext().setContextProperty(name, value)
    qml = '''import QtQuick
import QtQuick.Controls
import "%s" as Handler
ApplicationWindow {
    width:440; height:650; visible:true
    Handler.Theme { id:theme; dark:true }
    Handler.KnowledgeBaseView { anchors.fill:parent; theme:theme }
}''' % (HANDLER / 'thlib/ui/qml').as_uri()
    component = QQmlComponent(engine)
    component.setData(qml.encode(), QUrl.fromLocalFile(str(ROOT / 'tools/knowledge-reference.qml')))
    window = None
    try:
        for name in ('catalog', 'section', 'reader', 'editor', 'metadata', 'markdown', 'create', 'attachments'):
            record = data['section' if name == 'section' else 'article']
            controller._document = dict(record['document'])
            controller._identity = '' if name in ('catalog', 'create') else record['identity']
            controller._navigation_identity = controller._identity
            controller._editing = name in ('editor', 'metadata', 'markdown', 'create', 'attachments')
            controller._creating = name == 'create'
            controller._dirty = False
            controller._local_draft = False
            controller._open_article_pending = name != 'catalog'
            controller._parent_section = dict(identity=data['section']['identity'], title='Pipeline guide', description='Project documentation')
            if name == 'create':
                controller._document.update(title='Local new article', description='New local document', contentMarkdown='', contentText='')
            if name in ('metadata','markdown'):
                controller._document['title'] = 'Publishing guide revised'
            if name == 'markdown':
                controller._document['contentMarkdown'] += '\n\nDraft survives navigation.'
            controller._uploaded_attachments.replace([])
            if name == 'attachments':
                controller._document.update(title='Local new article',description='New local document',contentMarkdown='# Test\n\nNew article body.')
                controller._uploaded_attachments.replace([dict(token='fixture-file',snapshotKey='fixture-snapshot',title='тест.txt',extension='txt',sizeText='20 B',previewUrl='',webUrl='/assets/fixture.txt',isImage=False)])
            if name == 'section':
                controller._table_of_contents = [dict(identity=data['article']['identity'], title='Publishing guide', description='How to publish', kind='article', depth=1)]
            else:
                controller._table_of_contents = None
            metadata = record['articleMetadata']
            controller._article_metadata = dict(author=metadata['author'], authorDisplay=metadata['author'] or '—',
                createdLabel=metadata['createdAt'], updatedLabel=metadata['updatedAt'])
            rows = [dict(row, depth=int(bool(row['parentCode'])), hasChildren=row['kind'] == 'section', expanded=True, localDraft=False)
                    for row in data['article']['catalog']]
            navigation.replace(rows)
            controller.stateChanged.emit()
            for width, height in ((440, 650), (1200, 760)):
                window = component.create()
                if window is None:
                    raise RuntimeError('\n'.join(error.toString() for error in component.errors()))
                window.resize(width, height)
                QTest.qWait(300)
                if name in ('metadata','markdown','attachments'):
                    editor = window.findChild(QObject,'knowledgeArticleEditor')
                    if name == 'metadata': editor.setProperty('metadataExpanded',True)
                    if name == 'markdown': QMetaObject.invokeMethod(editor,'setContentMode',Q_ARG(str,'markdown'))
                    if name == 'attachments': editor.setProperty('attachmentsVisible',True)
                    QTest.qWait(100)
                if not window.grabWindow().save(str(OUTPUT / f'handler-{name}-{width}.png')):
                    raise RuntimeError('Knowledge QML screenshot failed')
                window.close(); window.deleteLater(); app.processEvents(); window = None
                controller._open_article_pending = name != 'catalog'
                print(f'Handler Knowledge Base {name} {width}', flush=True)
        sources = list((HANDLER / 'thlib/ui/qml').glob('Knowledge*.qml'))
        sources += [HANDLER / 'thlib/ui/knowledge.py', HANDLER / 'thlib/ui/knowledge_api.py',
                    HANDLER / 'thlib/ui/rich_text_document.py', HANDLER / 'thlib/ui/rich_text.py']
        (OUTPUT / 'source-manifest.json').write_text(json.dumps(dict(fixture='Private native one project from test_transport; fresh source QML, offline desktop controllers',
            sources={str(path.relative_to(HANDLER)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}), indent=2), encoding='utf8')
    finally:
        if window: window.close()
        controller._rich_text_document.deleteLater()
        engine.deleteLater(); app.processEvents()


if __name__ == '__main__': main()
