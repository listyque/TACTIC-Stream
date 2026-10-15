"""Install the delivered wheel and extracted Handler in an owned disposable root."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def qualify(delivery: Path, output: Path) -> None:
    manifest=json.loads((delivery/'manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['files']:
        path=delivery/entry['path']
        assert path.resolve().is_relative_to(delivery.resolve())
        digest=sha256()
        with path.open('rb') as source:
            for block in iter(lambda:source.read(1024*1024),b''):digest.update(block)
        assert digest.hexdigest()==entry['sha256'],entry['path']
    wheel,=delivery.glob('*.whl');archive,=delivery.glob('*-source.zip')
    with tempfile.TemporaryDirectory(prefix='file-installed-') as directory:
        root=Path(directory);environment=root/'environment'
        subprocess.run([sys.executable,'-m','venv',str(environment)],check=True,timeout=90,capture_output=True)
        python=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        subprocess.run([str(python),'-m','pip','install','--no-deps','--no-index',str(wheel)],check=True,timeout=90,capture_output=True)
        with zipfile.ZipFile(archive) as source:
            assert all((root/name).resolve().is_relative_to(root) for name in source.namelist())
            source.extractall(root)
        installed=environment/('Lib/site-packages' if os.name=='nt' else f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages')
        dependency_sites=[path for path in sys.path if Path(path).name in ('site-packages','dist-packages')]
        env={**os.environ,'PYTHONPATH':os.pathsep.join((str(installed),*dependency_sites,str(root/'TACTIC-Handler'))),
             'TACTIC_CONFIG_PATH':'','TACTIC_TMP_CONFIG_PATH':'','QT_QPA_PLATFORM':'offscreen',
             'QT_QUICK_CONTROLS_STYLE':'Material','QT_QUICK_BACKEND':'software'}
        probe=root/'probe.py'
        probe.write_text('''from pathlib import Path
import json,sys
import tactic_stream
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
root=Path(__file__).parent
assert Path(tactic_stream.__file__).resolve().is_relative_to(root/'environment')
store=Store(root/'data');store.initialize(hash_password('owned-installation-test'))
api=Api(store);ticket=api.get_ticket('admin','owned-installation-test')
args={'ticket':ticket,'project':'admin'}
api.dispatch('execute_cmd',(args,'tactic.command.project_template_cmd.ProjectTemplateInstallerCmd',{'project_code':'files','template_code':'perforce_like','project_title':'Installed files'}))
api.dispatch('execute_cmd',(args,'tactic.command.CreateProjectCmd',{'project_code':'classic','project_title':'Installed classic'}))
args['project']='files'
def call(action,**values):
    return api.dispatch('execute_cmd',(args,'tactic.command.file_project_cmd.FileProjectCmd',{'action':action,**values}))['info']
call('create_depot',code='main');call('create_stream',code='main',depot='main')
call('create_workspace',code='work',stream='main',local_root=str(root/'workspace'))
change=call('create_change',workspace='work')
assert change['state']=='pending' and call('capabilities')['administrator']
assert call('stream_graph')['items'][0]['code']=='main'
from thlib.environment import env_mode
env_mode.current_path=str(root/'client-cache')
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlEngine,QQmlComponent
from PySide6.QtCore import QUrl,QCoreApplication,QEvent
from thlib.ui.file_workspace import FileWorkspaceController
from thlib.ui.icon_font import qml_icon_bindings
from PySide6.QtCore import QObject,Signal
class Application(QObject):
    project_changed=Signal(str,str);server_state_changed=Signal();signing_out=Signal();project_state_changed=Signal()
    current_project_code='files'
app=QGuiApplication([]);owner=Application();controller=FileWorkspaceController(owner)
engine=QQmlEngine();warnings=[]
engine.warnings.connect(lambda rows:warnings.extend(row.toString() for row in rows))
handler=root/'TACTIC-Handler';qml=handler/'thlib/ui/qml'
for name,value in qml_icon_bindings(handler,engine).items():engine.rootContext().setContextProperty(name,value)
theme_component=QQmlComponent(engine,QUrl.fromLocalFile(str(qml/'Theme.qml')))
theme=theme_component.createWithInitialProperties({'dark':True})
component=QQmlComponent(engine,QUrl.fromLocalFile(str(qml/'FileWorkspaceView.qml')))
view=component.createWithInitialProperties({'theme':theme,'controller':controller})
assert view is not None,component.errors()
assert not warnings,warnings
result={'server_version':tactic_stream.__version__,'handler_version':json.loads((handler/'thlib/version.json').read_text()),'template':True,'classic_project':True,'native_command':True,'packaged_qml':True,'dependencies':'existing interpreter site reused; new wheel and extracted source paths verified'}
controller.shutdown()
for value in (view,controller,theme,component,theme_component,engine,owner):value.deleteLater()
QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
(root/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
''',encoding='utf-8')
        process=subprocess.run([str(python),'-S','-B','-X','utf8',str(probe)],cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
        if process.returncode:
            # Only the stack is diagnostic; native request logging contains disposable tickets.
            lines=process.stderr.splitlines()
            raise RuntimeError('Installed runtime probe failed: '+ '\n'.join(lines[-35:]))
        result=json.loads((root/'result.json').read_text(encoding='utf-8'))
        assert result['server_version']==manifest['server_version']
        output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();qualify(args.delivery.resolve(),args.output.resolve())
