"""Compare independent UI copies; copying between products is always explicit."""

import argparse
import hashlib
import json
from pathlib import Path
import re

SOURCE = Path(__file__).resolve().parents[1] / "src/tactic_stream/shared_ui"


def portable_files(root):
    return sorted(
        path
        for path in root.rglob("*")
        if path.suffix in (".mjs", ".json") and path.name != "manifest.json"
    )


def check_modules(root):
    for path in root.rglob("*.mjs"):
        imports = re.findall(
            r"""(?m)^(?:import\s+(?:[\w$*{},\s]+\sfrom\s*)?|export\s+(?:\{[\w$,\s]+\}|\*)\s+from\s*)["']([^"']+)["']""",
            path.read_text(encoding="utf-8"),
        )
        for reference in imports:
            target = (path.parent / reference).resolve()
            assert reference.startswith(".") and target.is_relative_to(
                root.resolve()
            ), f"External Frame import in {path}: {reference}"
            assert target.is_file(), f"Missing Frame import in {path}: {reference}"
            source_layer = path.relative_to(root).parts[0]
            target_layer = target.relative_to(root.resolve()).parts[0]
            assert not (source_layer == "core" and target_layer != "core"), (
                f"Core depends on {target_layer}: {path}"
            )
            assert not (
                source_layer == "controls" and target_layer not in ("core", "controls")
            ), f"Control depends on {target_layer}: {path}"


def sync(handler_root, check=False, copy_from=None, force=False):
    handler = Path(handler_root).resolve() / "thlib/ui/qml/tactic_frame"
    if copy_from:
        if check or copy_from not in ("stream", "handler"):
            raise ValueError("Choose either comparison or an explicit copy direction")
        source, target = (
            (SOURCE, handler) if copy_from == "stream" else (handler, SOURCE)
        )
        if not force and target.is_dir():
            import subprocess
            status = subprocess.run(
                ["git", "-C", str(target), "status", "--porcelain", "--", str(target)],
                capture_output=True, text=True, check=False,
            )
            if status.returncode == 0 and status.stdout.strip():
                raise RuntimeError(
                    f"Target Tactic Frame directory ({target}) has uncommitted changes; pass --force to overwrite:\n{status.stdout.strip()}"
                )
        check_modules(source)
        files = portable_files(source)
        assert files, "No Tactic Frame modules to copy"
        target.mkdir(parents=True, exist_ok=True)
        for path in files:
            destination = target / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(path.read_bytes())
        if (source / "README.md").is_file():
            (target / "README.md").write_bytes((source / "README.md").read_bytes())
        hashes = {
            path.relative_to(handler).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in portable_files(handler)
        }
        (handler / "manifest.json").write_text(
            json.dumps(
                {"source": "independent product copy", "sha256": hashes}, indent=2
            )
            + "\n",
            encoding="utf-8",
        )
    files = portable_files(SOURCE)
    check_modules(SOURCE)
    check_modules(handler)
    assert files, "No Stream Tactic Frame modules"
    assert {path.relative_to(SOURCE).as_posix() for path in files} == {
        path.relative_to(handler).as_posix() for path in portable_files(handler)
    }, "Different Tactic Frame module lists"
    for path in files:
        relative = path.relative_to(SOURCE)
        assert (handler / relative).read_bytes() == path.read_bytes(), (
            f"Tactic Frame copies differ: {relative}"
        )
    if (SOURCE / "README.md").is_file():
        assert (handler / "README.md").is_file() and (
            handler / "README.md"
        ).read_bytes() == (SOURCE / "README.md").read_bytes(), (
            "Tactic Frame contract documentation differs"
        )
    hashes = {
        path.relative_to(SOURCE).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in files
    }
    assert (
        json.loads((handler / "manifest.json").read_text(encoding="utf-8"))["sha256"]
        == hashes
    ), "Stale Handler manifest"
    print(
        f"{'Copied and checked' if copy_from else 'Checked'} {len(files)} Tactic Frame modules"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--handler-root", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Compare only (the default)")
    mode.add_argument(
        "--copy-from",
        choices=("stream", "handler"),
        help="Explicitly copy UI modules from this product",
    )
    parser.add_argument("--force", action="store_true", help="Allow overwriting uncommitted target Frame changes")
    args = parser.parse_args()
    sync(args.handler_root, args.check, args.copy_from, args.force)
