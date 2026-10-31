"""Build the installable example; keep caches and development files outside ZIP."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def build():
    root = Path(__file__).resolve().parents[2]
    source = root / 'examples/workspace_pulse'
    destination = root / 'releases/workspace-pulse-1.1.0.zip'
    destination.parent.mkdir(exist_ok=True)
    with ZipFile(destination, 'w', ZIP_DEFLATED) as archive:
        for name in ('manifest.xml', 'empty.spt', 'workspace.py', 'install.py',
                     'uninstall.py', 'README.md', 'README.ru.md'):
            archive.write(source / name, 'workspace_pulse/' + name)
    return destination


if __name__ == '__main__':
    print(build())
