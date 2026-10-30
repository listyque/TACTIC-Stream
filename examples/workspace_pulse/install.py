from pathlib import Path
import runpy

runpy.run_path(str(Path(kwargs['file_path']).with_name('workspace.py')))['install']()
