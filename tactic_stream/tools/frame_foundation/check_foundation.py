"""Compare portable foundations to the independently archived Handler Theme."""
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/grav/Tactic Stream/TH")
HERE = Path(__file__).resolve().parent
baseline = HERE / 'reference/foundation'
baseline.mkdir(parents=True, exist_ok=True)
with ZipFile('D:/grav/Tactic Stream/TS/backups/2026-10-15_103116_before_shared_ui_foundation/TH.zip') as archive:
    (baseline / 'Theme.qml').write_bytes(archive.read('thlib/ui/qml/Theme.qml'))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

app = QGuiApplication.instance() or QGuiApplication([])
engine = QQmlEngine()
warnings = []
engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
palettes = [([41,45,48],[120,166,196]), ([212,220,225],[61,117,153]), ([250,210,30],[160,30,190])]
cases = [{"style": style, "dark": dark, "base": base, "accent": accent}
         for style in ("md3", "material5", "fluent") for dark in (False, True) for base, accent in palettes]
module = (ROOT / "src/tactic_stream/shared_ui/core/foundation.mjs").as_uri()
script = 'import {palette,metrics,typography,motion,cssVariables,cssRoles} from ' + json.dumps(module) + ';const cases=' + json.dumps(cases) + ';console.log(JSON.stringify(cases.map(c=>({colors:palette(c.style,c.dark,c.base,c.accent),metrics:metrics(c.style),typography,cssRoles,css:cssVariables(c.style,c.dark,c.base,c.accent),motionVariants:Array.from({length:16},(_,mask)=>{const flags={click:!!(mask&1),hover:!!(mask&2),fade:!!(mask&4),popup:!!(mask&8)};return {flags,values:motion(c.style,flags)}})}))));'
actual = json.loads(subprocess.check_output(["node", "--input-type=module", "-e", script], text=True))
checks = 0
for native_root in (baseline, TH / "thlib/ui/qml"):
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(native_root / "Theme.qml")))
    assert component.isReady(), [error.toString() for error in component.errors()]
    for case, expected in zip(cases, actual):
        theme = component.createWithInitialProperties({"dark": case["dark"], "styleName": case["style"],
            "baseColor": QColor(*case["base"]), "accentColor": QColor(*case["accent"])})
        assert theme
        app.processEvents()
        for name, channels in expected["colors"].items():
            color = theme.property(name)
            assert isinstance(color, QColor), (native_root, name, color)
            measured = list(color.getRgbF())
            wanted = [channel / 255 for channel in channels[:3]] + [channels[3] if len(channels) == 4 else 1]
            # The old onError binding exposes black; the shared role fixes its contrast.
            if native_root != baseline or name != 'onError':
                assert all(abs(first-second) < .0001 for first, second in zip(measured, wanted)), (native_root, case, name, measured, wanted)
            checks += 1
        for name, value in expected["metrics"].items():
            if theme.metaObject().indexOfProperty(name) >= 0:
                assert theme.property(name) == value, (case, name, theme.property(name), value)
                checks += 1
        for variant in expected['motionVariants']:
            for flag, enabled in variant['flags'].items():
                theme.setProperty(flag + 'AnimationsEnabled', enabled)
            for name, value in variant['values'].items():
                if theme.metaObject().indexOfProperty(name) >= 0:
                    assert theme.property(name) == value, (native_root, case, variant['flags'], name, theme.property(name), value)
                    checks += 1
        theme.deleteLater()
assert not warnings, warnings
(HERE / "output/foundation.json").write_text(json.dumps({"cases": cases, "values": actual, "checks": checks}, indent=2), encoding="utf-8")
print("Original/current Handler vs shared foundation:", checks, "color and metric checks passed")
