"""Atomic publications and readers that permit replacement on Windows."""
import os
from pathlib import Path
import time
from uuid import uuid4


def read_text(path):
    if os.name != 'nt':
        return Path(path).read_text(encoding='utf-8')
    import ctypes
    from ctypes import wintypes
    import msvcrt
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateFileW(str(Path(path).absolute()), 0x80000000, 7, None, 3, 0x80, None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        kernel.CloseHandle(handle)
        raise
    with os.fdopen(descriptor, 'r', encoding='utf-8') as stream:
        return stream.read()


def replace(source, destination):
    for attempt in range(5):
        try:
            os.replace(source, destination)
            return
        except PermissionError as error:
            if os.name != 'nt' or error.winerror not in (5, 32, 33) or attempt == 4:
                raise
            time.sleep(.01 * (attempt + 1))


def write_text(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    try:
        with temporary.open('w', encoding='utf-8') as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
