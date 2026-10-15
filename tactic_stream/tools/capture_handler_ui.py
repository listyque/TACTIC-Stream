"""Capture the currently open Handler client; no mock QML or source changes.

D:/Python314/python.exe -B tools/capture_handler_ui.py [--navigation]
Navigation capture clicks the real menu button and closes it afterwards.
"""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys


def main():
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetDpiForWindow.argtypes = [wintypes.HWND]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    windows = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def visit(handle, _):
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(handle, title, len(title))
        if title.value.startswith('TACTIC-Handler') and user32.IsWindowVisible(handle):
            windows.append(handle)
        return True

    user32.EnumWindows(visit, 0)
    if len(windows) != 1:
        raise RuntimeError(f'Expected one Handler window, found {len(windows)}')
    handle = windows[0]
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication([])
    output = Path(__file__).resolve().parents[1] / '.screenshots/main-parity'
    output.mkdir(parents=True, exist_ok=True)
    rect = wintypes.RECT()
    user32.GetClientRect(handle, ctypes.byref(rect))
    scale = user32.GetDpiForWindow(handle) / 96
    (output / 'viewport.json').write_text(json.dumps({'width': round(rect.right / scale), 'height': round(rect.bottom / scale), 'deviceScaleFactor': scale}), encoding='utf-8')
    errors = []

    def click_menu():
        point = (round(22 * scale) << 16) | round(22 * scale)
        user32.PostMessageW(handle, 0x0201, 1, point)
        user32.PostMessageW(handle, 0x0202, 0, point)

    def save():
        try:
            suffix = 'navigation' if '--navigation' in sys.argv else 'main'
            pixmap = app.primaryScreen().grabWindow(handle)
            if pixmap.isNull() or not pixmap.save(str(output / f'handler-{suffix}.png')):
                raise RuntimeError('Cannot capture live Handler window')
            print(f'Live Handler client captured: {rect.right}x{rect.bottom}, scale {scale}')
        except Exception as error:
            errors.append(error)
        finally:
            if '--navigation' in sys.argv:
                click_menu()
            app.quit()

    if '--navigation' in sys.argv:
        click_menu()
    QTimer.singleShot(700, save)
    app.exec()
    if errors:
        raise errors[0]


if __name__ == '__main__':
    main()
