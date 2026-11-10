"""Compile Handler's existing Windows launchers and self-contained installer."""
from hashlib import file_digest
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def compiler():
    path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    if not path.is_file():
        raise FileNotFoundError('The Windows .NET Framework C# compiler is required: ' + str(path))
    return path


def launchers(handler, output):
    source = handler / 'tools/setup/Launcher.cs'
    icon = handler / 'thlib/ui/assets/tactic_favicon.ico'
    for name, define in [('TACTIC Handler.exe', ''), ('TH Setup.exe', 'SETUP_WIZARD'),
                         ('TH Setup Builder.exe', 'SETUP_BUILDER')]:
        command = [str(compiler()), '/nologo', '/utf8output', '/target:winexe', '/platform:x64', '/optimize+',
                   '/reference:System.Windows.Forms.dll', '/win32icon:' + str(icon),
                   '/out:' + str(output / name)]
        if define:
            command.append('/define:' + define)
        subprocess.run([*command, str(source)], check=True, capture_output=True, text=True, timeout=90)


def installer(handler, bundle, target):
    """The installer verifies a complete public payload before touching a destination."""
    if target.exists():
        raise FileExistsError(target)
    version = '.'.join(json.loads((handler / 'thlib/version.json').read_text())[key]
                       for key in ('major', 'minor', 'build', 'revision'))
    if not (bundle / 'SHA256SUMS').is_file() or not (bundle / 'BUILD.json').is_file():
        raise FileNotFoundError('Handler installer requires BUILD.json and SHA256SUMS')
    with tempfile.TemporaryDirectory(prefix='handler-installer-') as temporary:
        temporary = Path(temporary)
        payload = temporary / 'handler.zip'
        with zipfile.ZipFile(payload, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(bundle.rglob('*')):
                if path.is_symlink():
                    raise ValueError('Installer payload must not contain symbolic links')
                if path.is_file():
                    archive.write(path, 'TH/' + path.relative_to(bundle).as_posix())
        with payload.open('rb') as stream:
            digest = file_digest(stream, 'sha256').hexdigest()
        constants = temporary / 'PayloadHash.cs'
        constants.write_text('internal static class PayloadHash { public const string Value = "' + digest
                            + '"; public const string Version = "' + version + '"; }\n', encoding='utf-8')
        staged = temporary / 'setup.exe'
        subprocess.run([str(compiler()), '/nologo', '/utf8output', '/target:winexe', '/platform:x64', '/optimize+',
            '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll',
            '/reference:System.IO.Compression.dll', '/reference:System.IO.Compression.FileSystem.dll',
            '/reference:System.Web.Extensions.dll', '/out:' + str(staged),
            '/win32icon:' + str(handler / 'thlib/ui/assets/tactic_favicon.ico'),
            '/resource:' + str(payload) + ',handler.zip', str(constants),
            str(handler / 'tools/setup/Installer.cs'), str(handler / 'tools/setup/SetupPresets.cs')],
            check=True, capture_output=True, text=True, timeout=180)
        # The native Setup Builder reads this same public preset footer.
        subprocess.run([sys.executable, '-B', '-c',
            'from pathlib import Path; from thlib.ui.setup_package import initialize_installer; '
            'import sys; initialize_installer(Path(sys.argv[1]), sys.argv[2])', str(staged), version],
            cwd=handler, check=True, timeout=30)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as destination, staged.open('rb') as source:
            import shutil
            shutil.copyfileobj(source, destination)
    return target
