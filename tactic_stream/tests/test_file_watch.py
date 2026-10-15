"""Bounded native Windows change notifications and cancellation."""
import os
from contextlib import closing
import json
import sqlite3
from pathlib import Path
import struct
import tempfile
from time import monotonic
import unittest

from tactic_client_lib.file_watch import WorkspaceWatch


class FileWatchTest(unittest.TestCase):
    def test_notifications_invalidate_preserved_metadata_and_classify_missing_files(self):
        from tactic_client_lib.file_workspace import watched_changes
        from tactic_client_lib.file_transfer import fingerprint
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'edited').write_bytes(b'original')
            cache=root/'index.sqlite'
            with closing(sqlite3.connect(cache)) as db:
                db.execute('CREATE TABLE local(path TEXT PRIMARY KEY,data TEXT)')
                db.execute('INSERT INTO local VALUES(?,?)',('edited',json.dumps({'fingerprint':list(fingerprint(root/'edited')),'local_status':'current'})))
                db.execute('INSERT INTO local VALUES(?,?)',('ignored',json.dumps({'local_status':'ignored'})))
                db.commit()
            (root/'added').write_bytes(b'new')
            self.assertEqual(watched_changes(cache,root,['edited','added','removed','ignored']),
                             {'edited':'modified','added':'added','removed':'missing'})
            from tactic_client_lib.file_workspace import inspect_local
            row={'local_path':'edited','action':'write','file':{'sha256':'previous'}}
            inspect_local(cache,root,[row])
            self.assertEqual(row['local_status'],'modified')
            self.assertFalse(row['staged_current'],'A preserved timestamp must not restore the staged-copy indication')

    def record(self,path):
        name=path.encode('utf-16-le')
        return struct.pack('<III',0,1,len(name))+name

    def test_notification_queue_is_bounded_and_overflow_is_explicit(self):
        watcher=WorkspaceWatch('unused')
        watcher.LIMIT=2
        for path in ('first','folder\\second','third'):
            watcher.collect(self.record(path))
        result=watcher.take()
        self.assertEqual(result['paths'],['first','folder/second'])
        self.assertTrue(result['overflow'])
        self.assertEqual(watcher.take()['paths'],[])
        watcher.collect(b'')
        self.assertTrue(watcher.take()['overflow'])
        watcher.collect(b'invalid')
        self.assertTrue(watcher.take()['overflow'])

    @unittest.skipUnless(os.name=='nt','Native Windows filesystem notifications')
    def test_real_recursive_unicode_changes_and_stop_leave_no_worker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            watcher=WorkspaceWatch(root)
            watcher.start()
            try:
                self.assertTrue(watcher.ready.wait(3))
                self.assertEqual(watcher.take()['error'],'')
                (root/'新しい').mkdir()
                (root/'新しい'/'файл.txt').write_text('first',encoding='utf-8')
                deadline=monotonic()+3
                seen=set()
                while monotonic()<deadline and '新しい/файл.txt' not in seen:
                    result=watcher.take()
                    self.assertEqual(result['error'],'')
                    seen.update(result['paths'])
                    watcher.stop_event.wait(.01)
                self.assertIn('新しい/файл.txt',seen)
            finally:
                watcher.stop()
                watcher.thread.join(3)
                self.assertFalse(watcher.thread.is_alive(),'Watcher cancellation must release the native directory handle')
