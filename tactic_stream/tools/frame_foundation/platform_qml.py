"""Measure the actual old/new list update through a settled native frame."""

import json
import os
from pathlib import Path
from statistics import median
import sys
from time import perf_counter
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
HANDLER = Path("D:/grav/Tactic Stream/TH")
os.environ.update(
    QT_QPA_PLATFORM="offscreen",
    QT_QUICK_BACKEND="software",
    TMP=str(ROOT / ".tmp/frame-tests"),
    TEMP=str(ROOT / ".tmp/frame-tests"),
)
sys.path.insert(0, str(HANDLER))
from tests import test_frame_platform as fixture
from tests.profile_ui_responsiveness import frame


def main():
    original = ROOT / ".tmp/frame-phase0-original"
    with ZipFile(ROOT / ".tmp/frame-phase0-original.zip") as archive:
        for name in archive.namelist():
            target = (original / name).resolve()
            assert target.is_relative_to(original.resolve())
            if name.endswith("/"):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    fixture.FramePlatformTests.setUpClass()
    samples = []
    for label, directory in [
        ("original", original / "thlib/ui/qml"),
        ("current", HANDLER / "thlib/ui/qml"),
    ]:
        fixture.QML = directory
        case = fixture.FramePlatformTests()
        case.setUp()
        try:
            for count in (1000, 4000):
                case.evaluate(f"populate({count})")
                frame(case.window)
                timings = []
                for _ in range(3):
                    start = perf_counter()
                    case.evaluate("reverse()")
                    frame(case.window)
                    timings.append(round((perf_counter() - start) * 1000, 2))
                samples.append(
                    dict(
                        label=label,
                        count=count,
                        milliseconds=timings,
                        median=median(timings),
                    )
                )
                print(samples[-1], flush=True)
        finally:
            case.doCleanups()
    output = ROOT / "tools/frame_foundation/output/platform"
    output.mkdir(parents=True, exist_ok=True)
    (output / "list-performance.json").write_text(
        json.dumps(samples, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
