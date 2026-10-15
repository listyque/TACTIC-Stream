"""Install changed pinned dependencies in a persistent Docker volume."""
from importlib.metadata import PackageNotFoundError, version
import subprocess
import sys
import tomllib


with open('/opt/stream-pyproject.toml', 'rb') as source:
    requirements = tomllib.load(source)['project']['dependencies']
missing = []
for requirement in requirements:
    name, wanted = requirement.split('==', 1)
    try:
        current = version(name)
    except PackageNotFoundError:
        current = None
    if current != wanted:
        missing.append(requirement)
if missing:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', '--target',
                    '/opt/python-packages', *missing], check=True)
    # Verify in a fresh interpreter, including newly installed metadata.
    subprocess.run([sys.executable, '-c',
                    'from importlib.metadata import version; import sys; '
                    'assert all(version(r.split("==",1)[0]) == r.split("==",1)[1] for r in sys.argv[1:])',
                    *requirements], check=True)
