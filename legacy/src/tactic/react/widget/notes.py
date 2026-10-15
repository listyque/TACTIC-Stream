
__all__ = [
        'GetNoteListCmd',
        'AddNoteCmd',
        'NoteAttachImageCmd'
]

from pyasm.common import Common, Environment
from pyasm.biz import Snapshot
from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.checkin import FileCheckin

import os


class GetNoteListCmd(Command):

    def execute(self):

        parent_key = self.kwargs.get("parent_key")
        if not parent_key:
            raise Exception("No parent key given")

        parent = Search.get_by_search_key(parent_key)


        search = Search("sthpw/note")
        search.add_filter("search_type", parent.get_search_type())
        search.add_filter("search_code", parent.get_code())
        notes = search.get_sobjects()

        note_list = search.get_sobject_dicts(notes)

        note_lookup = {}
        for note in note_list:
            note_lookup[note.get("code")] = note

        snapshots = Snapshot.get_by_sobjects(notes, is_latest=True, process="publish")
        for snapshot in snapshots:
            search_code = snapshot.get_value("search_code")
            web_path = snapshot.get_web_path_by_type("icon")
            path = snapshot.get_web_path_by_type()
            if not web_path:
                web_path = path

            note = note_lookup[search_code]
            attachments = note.get("attachments")
            if attachments == None:
                attachments = []
                note["attachments"] = attachments

            attachments.append( {
                "web": web_path,
                "main": path
            } )



        return note_list



class AddNoteCmd(Command):

    def execute(self):

        user = Environment.get_login()
        login = user.get_value("login")

        message = self.kwargs.get("message")

        parent_key = self.kwargs.get("parent_key")
        parent = Search.get_by_search_key(parent_key)
        if not parent:
            raise Exception("Parent does not exist")

        code = self.kwargs.get("code")
        if code:
            note = Search.get_by_code("sthpw/note", code)
            if not note:
                raise Exception("No note with code [%s]" % code)
        else:
            note = SearchType.create("sthpw/note")
            note.set_value("login", login)
            note.set_parent(parent)

        note.set_value("note", message)
        note.commit()

        self.note = note

        return note.get_sobject_dict()


class NoteAttachImageCmd(Command):

    def execute(self):

        name = self.kwargs.get("name")
        code = self.kwargs.get("code")

        parent_key = self.kwargs.get("parent_key")
        parent = Search.get_by_search_key(parent_key)
        if not parent:
            raise Exception("Parent [%s] not found" % parent_key)


        message = "Attach Image: %s" % name

        # people will add files before the note is created. 
        # if this is done, create a new which can be replace later with a message
        if code:
            note = Search.get_by_code("sthpw/note", code)
            if not note:
                raise Exception("Note [%s] does not exist" % code)
        else:
            cmd = AddNoteCmd(parent_key=parent_key, message=message)
            cmd.execute()

            note = cmd.note


        tmp_dir = Environment.get_upload_dir()

        path = "%s/%s" % (tmp_dir, name)
        if not os.path.exists(path):
            raise Exception("No file [%s] uploaded" % name)

        checkin = FileCheckin(note, path, context="publish/%s" % name)
        checkin.execute()

        return note.get_sobject_dict()



