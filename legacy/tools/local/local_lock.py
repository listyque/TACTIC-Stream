"""Cooperative local server/upgrade lock, with shared cluster lifetime ownership.

Standalone/upgrade use exclusive mode. The cluster supervisor and every worker
hold shared mode, so an orphaned worker still prevents an offline upgrade.
A second, exclusive owner lock prevents two supervisors starting one install.
Old local launchers' exclusive flock/msvcrt locks conflict with this byte range.
"""
from contextlib import contextmanager
import os
from pathlib import Path

@contextmanager
def local_lock(data: Path, *, shared=False, name='.native-local.lock'):
    data.mkdir(parents=True,exist_ok=True)
    path=data/name
    handle=path.open('a+b')
    win_overlapped = None
    win_handle = None
    try:
        handle.seek(0,os.SEEK_END)
        if handle.tell()==0:handle.write(b'0');handle.flush()
        handle.seek(0)
        try:
            if os.name=='nt':
                import ctypes
                from ctypes import wintypes
                import msvcrt
                class OVERLAPPED(ctypes.Structure):
                    _fields_=[('Internal',ctypes.c_size_t),('InternalHigh',ctypes.c_size_t),
                              ('Offset',wintypes.DWORD),('OffsetHigh',wintypes.DWORD),('hEvent',wintypes.HANDLE)]
                kernel=ctypes.WinDLL('kernel32',use_last_error=True)
                lock=kernel.LockFileEx
                lock.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(OVERLAPPED)]
                lock.restype=wintypes.BOOL
                win_handle=wintypes.HANDLE(msvcrt.get_osfhandle(handle.fileno()))
                win_overlapped=OVERLAPPED()
                flags=1 | (0 if shared else 2)  # FAIL_IMMEDIATELY | EXCLUSIVE_LOCK
                if not lock(win_handle,flags,0,1,0,ctypes.byref(win_overlapped)):
                    raise ctypes.WinError(ctypes.get_last_error())
            else:
                import fcntl
                fcntl.flock(handle.fileno(),(fcntl.LOCK_SH if shared else fcntl.LOCK_EX)|fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('Another local TACTIC server/upgrade is active. Stop it before continuing.') from exc
        yield
    finally:
        # Closing the handle releases the OS lock, including on process death.
        handle.close()
