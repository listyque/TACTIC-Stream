"""Build an isolated wheel and verify every portable Frame module it ships."""

from contextlib import redirect_stderr, redirect_stdout
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

import setuptools.build_meta

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "src/tactic_stream/shared_ui"
    output = ROOT / "tools/frame_foundation/output"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="frame-wheel-", dir=ROOT / ".tmp"
    ) as temporary:
        work = Path(temporary)
        with (
            (work / "build.log").open("w", encoding="utf-8") as log,
            redirect_stdout(log),
            redirect_stderr(log),
        ):
            wheel = setuptools.build_meta.build_wheel(
                str(work / "wheel"),
                config_settings={
                    "--global-option": ["build", "--build-base", str(work / "build")]
                },
            )
        with ZipFile(work / "wheel" / wheel) as archive:
            prefix = "tactic_stream/shared_ui/"
            shipped = {
                name.removeprefix(prefix)
                for name in archive.namelist()
                if name.startswith(prefix) and name.endswith((".mjs", ".json"))
            }
            expected = {
                path.relative_to(source).as_posix()
                for path in source.rglob("*")
                if path.suffix in (".mjs", ".json")
            }
            assert shipped == expected, dict(
                missing=sorted(expected - shipped), extra=sorted(shipped - expected)
            )
            for name in shipped | {"README.md"}:
                data = archive.read(prefix + name)
                assert data == (source / name).read_bytes(), name
                target = work / "installed" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        paths = [
            str(work / "installed" / name)
            for name in sorted(shipped)
            if name.endswith(".mjs")
        ]
        script = "import {pathToFileURL} from 'node:url'; for (const path of process.argv.slice(1)) await import(pathToFileURL(path));"
        subprocess.run(
            [shutil.which("node"), "--input-type=module", "--eval", script, *paths],
            cwd=work,
            check=True,
            timeout=30,
        )
    report = dict(
        wheel=wheel,
        modules=len(expected),
        exactFiles=True,
        exactBytes=True,
        isolatedImports=True,
    )
    (output / "package.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        "Independent wheel: all",
        len(expected),
        "Frame modules and imports passed; no stale flat copies",
    )


if __name__ == "__main__":
    main()
