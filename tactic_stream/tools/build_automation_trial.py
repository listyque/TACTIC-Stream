"""Build the optional offline-execution image from curated source, never runtime settings."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handler-root', type=Path, required=True)
    parser.add_argument('--tag', default='tactic-automation-trial:local')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='tactic-trial-build-') as temporary:
        context = Path(temporary)
        ignore = shutil.ignore_patterns('__pycache__', '*.pyc', '.git', 'settings', 'cache', 'logs')
        shutil.copytree(ROOT/'src', context/'stream', ignore=ignore)
        for folder in ('thlib', 'tactic_handler_api', 'tactic_handler_dcc', 'side_tools/frame_tool'):
            shutil.copytree(args.handler_root/folder, context/'handler'/folder, ignore=ignore)
        shutil.copytree(ROOT/'deploy/automation-trial/runtime', context/'runtime')
        shutil.copyfile(ROOT/'deploy/automation-trial/Dockerfile', context/'Dockerfile')
        for filename in ('pyproject.toml', 'README.md'):
            shutil.copyfile(ROOT/filename, context/filename)
        subprocess.run(['docker', 'build', '--tag', args.tag, str(context)], check=True)
    subprocess.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', args.tag], check=True)


if __name__ == '__main__':
    main()
