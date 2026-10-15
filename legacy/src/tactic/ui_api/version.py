"""Single source of native UI version for runtime and build diagnostics."""
from pathlib import Path
VERSION=(Path(__file__).resolve().parents[3]/'NATIVE_UI_VERSION').read_text(encoding='utf-8').strip()
BUILD_VERSION=VERSION+'.0-source-fork'
