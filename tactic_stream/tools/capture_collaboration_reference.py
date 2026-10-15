"""Current unmodified Handler QML with its isolated task/message fixtures."""
from pathlib import Path
import hashlib
import json
import os
import sys
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
HANDLER = Path('D:/code/th_codex')
OUTPUT = ROOT / '.screenshots/collaboration-current'

def main():
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['QT_QUICK_BACKEND'] = 'software'
    os.environ['QT_SCALE_FACTOR'] = '1'
    sys.path.insert(0,str(HANDLER))
    from tests.qt_application import gui_test_application
    from tests.test_tasks_controller import _TaskInspectorController, _TaskInspectorTasksController, FakeApplication
    from tests.test_notes_qml import _Application, _SObject
    from thlib.ui.communication import CommunicationController
    from thlib.ui.work_hours import WorkHoursController
    from thlib.ui.communication_feed import MessagesController
    from thlib.ui.message_attachments import AttachmentUploadController, ChatAttachmentController
    from thlib.ui.workspace_models.records import RecordListModel
    from thlib.ui.icon_font import qml_icon_bindings
    from PySide6.QtCore import QObject, Signal, QUrl
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtTest import QTest

    OUTPUT.mkdir(parents=True,exist_ok=True)
    app = gui_test_application()
    for font in ('segoeui.ttf','segoeuib.ttf'): QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font)
    engine = QQmlEngine(); window = QQuickWindow(); view = None
    qml = HANDLER / 'thlib/ui/qml'; engine.addImportPath(str(qml)); context = engine.rootContext()
    for name,value in qml_icon_bindings(HANDLER,engine).items(): context.setContextProperty(name,value)
    inspector = _TaskInspectorController(); tasks = _TaskInspectorTasksController()
    users = RecordListModel(('login','displayName','initials','avatarUrl'),[dict(login='artist',displayName='Artist',initials='AR',avatarUrl='')])
    hours = WorkHoursController(FakeApplication())
    for name,value in dict(tasksController=tasks,userListModel=users,workHoursController=hours).items(): context.setContextProperty(name,value)
    component = QQmlComponent(engine,QUrl.fromLocalFile(str(qml/'Theme.qml')))
    theme = component.createWithInitialProperties(dict(dark=True)); assert theme,component.errors()
    metadata = dict(capturedAt=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),sources={},images={})
    def render(file,properties):
        nonlocal view,component
        if view: view.setParentItem(None); view.deleteLater(); app.processEvents()
        component = QQmlComponent(engine,QUrl.fromLocalFile(str(qml/file)))
        view = component.createWithInitialProperties(dict(theme=theme,**properties))
        assert view,[error.toString() for error in component.errors()]
        view.setParentItem(window.contentItem())
    def capture(name,width,height):
        window.resize(width,height); view.setSize(window.size()); window.show()
        for _ in range(4): app.processEvents(); QTest.qWait(80)
        image = window.grabWindow(); assert not image.isNull() and image.save(str(OUTPUT/(name+'.png')))
        metadata['images'][name] = dict(logicalWidth=width,logicalHeight=height,dpr=window.devicePixelRatio())
    try:
        render('TaskInspector.qml',dict(controller=inspector))
        inspector.set_task(code='',processRow=-1); capture('th-inspector-empty',620,214)
        inspector.set_task(code='TASK001',processRow=1,context='publish',status='Ready',progress=40,progressInput='40'); capture('th-inspector-task',620,300)
        inspector.set_task(dirty=True); capture('th-inspector-draft',620,300)
        inspector.set_expanded(False); capture('th-inspector-collapsed',620,96)
        inspector.set_expanded(True); inspector.set_progress(dict(state='ready',items=[dict(parentTitle='Related child',process='Model',assigned='Artist',status='Ready',taskKey='TASK_CHILD')],objectCount=1)); capture('th-inspector-related',620,214)
        class MessageApplication(_Application): project_changed = Signal(str,str)
        application = MessageApplication()
        with patch('thlib.ui.message_attachments.env_read_config',return_value={}): chat_files=ChatAttachmentController(application)
        with patch('thlib.ui.communication_feed.env_read_config',return_value={}): messages = MessagesController(application)
        messages.load = Mock(); messages.set_visible = Mock(); messages._initialized = True; messages._conversation_id = 'CHAT001'
        chats=[]
        for code,title,names,count in [('FAVORITES','Favorites',[],0),('GROUP','Lighting review',['admin','artist','reviewer'],35),('CHAT001','artist',['admin','artist'],3)]:
            row=dict.fromkeys(messages.conversations._roles,'')
            row.update(conversationId=code,title=title,recipients=names,recipientNames=names,participantCount=len(names),messageCount=count,attachmentCount=0,isPersonalNotes=not names,selected=code=='CHAT001',avatarUrl='',initials='AR' if code=='CHAT001' else 'LR',acronym='AR' if code=='CHAT001' else 'LR',colorIndex=2,unread=0,mentionCount=0,lastSender='admin' if count else '',lastMessageSummary='Thank you! I will take a look.' if code=='CHAT001' else '',memberSummary=str(len(names))+' members',canManage=True,canRename=True,canDelete=True,canAddMembers=True,canClearPersonal=not names,presenceKnown=False,online=False)
            chats.append(row)
        messages.conversations.replace(chats)
        rows = []
        for index,body in enumerate(['The new collection is ready.\nPlease review the lighting.','I have also updated the textures.','Thank you! I will take a look.']):
            rows.append(dict(messageId='MSG00'+str(index),sender='artist',senderDisplay='Artist',avatarUrl='',initials='AR',senderColor='#60a7ca',body=body,bodyHtml=body,displayHtml=body,skeyPreviews=[],timestamp='2026-10-11 10:00:00',timePretty='10:00',timeSimple='',isOwn=False,unread=False,attachments=[],canEdit=False,edited=False,pinned=False,editedBy='',editedAt='',editHistory=[],replyTo={},forwardedFrom={},forwardSelected=False,reactions=[],deliveryState='',deliveryText='',deliveryRecipientCount=0,deliveryDeliveredCount=0,deliveryReadCount=0,groupFirst=index==0,groupLast=index==1))
        for index,row in enumerate(rows):
            row.update(sender='admin' if index==2 else 'artist',senderDisplay='admin' if index==2 else 'artist',initials='AD' if index==2 else 'AR',isOwn=index==2,groupFirst=index in (0,2),groupLast=index in (1,2),bodyHtml=row['body'].replace('\n','<br>'),displayHtml=row['body'].replace('\n','<br>'))
        messages.messages.replace(rows)
        for name,value in dict(messagesController=messages,messageConversationModel=messages.conversations,messageSurfaceModel=messages.message_surfaces,userController=QObject(),messageAttachments=chat_files,messageAttachmentDraftModel=chat_files.model).items(): context.setContextProperty(name,value)
        render('MessagesView.qml',{}); capture('th-messages',1062,736)
        notes_app = _Application()
        with patch('thlib.ui.communication.env_read_config',return_value={}): notes = CommunicationController(notes_app)
        with patch('thlib.ui.message_attachments.env_read_config',return_value={}): note_files=AttachmentUploadController(notes_app)
        notes_app.workspace_state._selected_sobject = _SObject({'code':'ASSET001','name':'Hero asset'},'asset/asset?code=ASSET001')
        notes._selected_object = {'title':'Hero asset','type':'Asset'}
        notes._process_choices = [{'value':'publish','label':'Publish','type':'built-in','count':2}]
        notes._task_expanded = False
        notes._visible = True
        note_rows = []
        for index,body in enumerate(['Browser discussion','Sent from browser']):
            note_rows.append(dict(noteId=str(index),searchKey='sthpw/note?id='+str(index),author='admin',authorDisplay='admin',avatarUrl='',initials='AD',time='2026-10-11 10:00:00',timePretty='Just now',timeSimple='',body=body,bodyHtml=body,displayHtml=body,skeyPreviews=[],process='publish',isOwn=True,unread=False,attachments=[],attachmentCount=0,entryType='note',authorColor='#78a6c4',statusFrom='',statusTo='',statusColor='#78a6c4',canEdit=True,canDelete=True,statusTimelineBefore=False,statusTimelineAfter=False))
        notes._note_records = note_rows
        notes_app.workspace_state.note_model = RecordListModel(tuple(note_rows[0]),note_rows)
        for name,value in dict(communicationController=notes,noteModel=notes_app.workspace_state.note_model,noteAttachmentDraftModel=note_files.model,noteAttachments=note_files,emojiCatalog=QObject()).items(): context.setContextProperty(name,value)
        with patch('thlib.ui.communication.env_write_config'):
            render('CommunicationView.qml',{}); capture('th-notes',620,600)
        assert notes_app.workspace_state.note_model.count() == 2, 'Native history fixture must remain visible'
        def items(item):
            yield item
            for child in item.childItems(): yield from items(child)
        assert len([item for item in items(view) if item.objectName() == 'noteTimelineBubble']) == 2, 'Both QML delegates must render'
        with patch('thlib.ui.communication.env_write_config'):
            notes_app.workspace_state.note_model.replace(note_rows[:1]); capture('th-notes-single',620,600)
        assert notes_app.workspace_state.note_model.count() == 1
        for file in ['TaskInspector.qml','CommunicationView.qml','TasksWorkspaceView.qml','TaskBrowserTable.qml','TaskProcessPanel.qml','TaskGanttView.qml','TaskCalendarView.qml','MessagesView.qml','MessagesTimeline.qml','MessageTimelineFrame.qml','NotesTimelinePosition.qml','WorkHoursSummary.qml','controls/Typography.qml']:
            metadata['sources']['thlib/ui/qml/'+file] = hashlib.sha256((qml/file).read_bytes()).hexdigest()
        for file in ['thlib/ui/communication.py','thlib/ui/tasks.py','thlib/ui/communication_feed.py','thlib/ui/composer_drafts.py','thlib/ui/message_attachments.py']:
            metadata['sources'][file] = hashlib.sha256((HANDLER/file).read_bytes()).hexdigest()
        (OUTPUT/'native.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')
        print('Saved current QML:',OUTPUT)
    finally:
        window.close()
        if view: view.setParentItem(None); view.deleteLater()
        engine.deleteLater(); app.processEvents()

if __name__ == '__main__': main()

