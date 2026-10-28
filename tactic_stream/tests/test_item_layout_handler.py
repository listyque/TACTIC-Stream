"""Independent native/browser Frame editor parity; server XML semantics are tested in test_item_layout."""
import os,subprocess,sys,unittest
from pathlib import Path

class HandlerLayouts(unittest.TestCase):
    def test_page_editor(self):
        root=Path(__file__).resolve().parents[1]
        environment=dict(os.environ,PLAYWRIGHT_BROWSERS_PATH=str(root/'.browser-cache'),
                         QSG_RENDER_LOOP='basic',QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software')
        output=root/'.screenshots/page-editor'
        output.mkdir(parents=True,exist_ok=True)
        for index,(command,cwd) in enumerate([
            ([sys.executable,'tools/frame_layout/capture_page.py'],root),
            (['node','tests/page_editor_parity.mjs'],root/'frontend')]):
            log=output/f'frame-{index}.log'
            with log.open('w',encoding='utf-8') as stream:
                result=subprocess.run(command,cwd=cwd,env=environment,stdout=stream,# 128 paired states exceed the old 104-state two-minute budget.
                                      stderr=subprocess.STDOUT,timeout=180)
            self.assertEqual(result.returncode,0,log.read_text(encoding='utf-8'))

    def test_native_editor(self):
        root=Path(__file__).resolve().parents[1]
        environment=dict(os.environ,FRAME_CAPTURE_QUICK='0',STREAM_BROWSER_CHANNEL=os.environ.get('STREAM_BROWSER_CHANNEL','msedge'),TMP=str(root/'.tmp/frame-tests'),TEMP=str(root/'.tmp/frame-tests'))
        output=root/'.screenshots/item-layout-handler';output.mkdir(parents=True,exist_ok=True)
        commands=[([sys.executable,'-B','-X','utf8','tools/frame_layout/capture_qml.py'],root),(['node','tests/frame_layout.mjs'],root/'frontend')]
        for index,(command,cwd) in enumerate(commands):
            log=output/f'frame-{index}.log'
            with log.open('w',encoding='utf8') as stream:
                result=subprocess.run(command,cwd=cwd,env=environment,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
            self.assertEqual(result.returncode,0,log.read_text(encoding='utf8'))
