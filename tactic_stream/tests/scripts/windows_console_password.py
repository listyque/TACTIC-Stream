"""Feed only the native first-run console descending from the owned Electron test PID."""
import ctypes
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


class Key(ctypes.Structure):
    _fields_ = [('down', w.BOOL), ('repeat', w.WORD), ('virtual', w.WORD), ('scan', w.WORD),
                ('char', w.WCHAR), ('controls', w.DWORD)]


class Event(ctypes.Union):
    _fields_ = [('key', Key), ('padding', ctypes.c_byte * 16)]


class Record(ctypes.Structure):
    _fields_ = [('kind', w.WORD), ('event', Event)]


def initialize(bundle, parent):
    environment = dict(os.environ, L12_RUNTIME_PYTHON=str(bundle / 'runtime/python.exe'))
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    query = "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $env:L12_RUNTIME_PYTHON } | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.AttachConsole.argtypes = [w.DWORD]
    kernel.AttachConsole.restype = w.BOOL
    kernel.FreeConsole()
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        result = subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-Command', query],
                                env=environment, check=True, capture_output=True, text=True,
                                creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
        processes = json.loads(result.stdout) if result.stdout.strip() else []
        if isinstance(processes, dict):
            processes = [processes]
        owned = {parent}
        for _ in processes:
            owned.update(p['ProcessId'] for p in processes if p['ParentProcessId'] in owned)
        matches = [p for p in processes if p['ProcessId'] in owned and
                   re.search(r'\binit\s+--if-needed\s*$', p['CommandLine'] or '')]
        if matches:
            assert len(matches) == 1, 'Ambiguous first-run console'
            if kernel.AttachConsole(matches[0]['ProcessId']):
                break
        time.sleep(.1)
    else:
        raise TimeoutError('Owned first-run console did not appear')
    kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
    kernel.CreateFileW.restype = w.HANDLE
    kernel.WriteConsoleInputW.argtypes = [w.HANDLE, ctypes.POINTER(Record), w.DWORD, ctypes.POINTER(w.DWORD)]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    console = kernel.CreateFileW('CONIN$', 0x40000000, 3, None, 3, 0, None)
    try:
        password = os.environ['WINDOWS_CHECK_PASSWORD']
        assert password and '\r' not in password and '\n' not in password
        text = (password + '\r') * 2
        records = (Record * len(text))()
        for index, char in enumerate(text):
            records[index].kind = 1
            records[index].event.key = Key(True, 1, 13 if char == '\r' else 0, 0, char, 0)
        written = w.DWORD()
        if not kernel.WriteConsoleInputW(console, records, len(records), ctypes.byref(written)):
            raise ctypes.WinError(ctypes.get_last_error())
        assert written.value == len(records)
    finally:
        kernel.CloseHandle(console)
        kernel.FreeConsole()


if __name__ == '__main__':
    initialize(Path(sys.argv[1]).resolve(), int(sys.argv[2]))
