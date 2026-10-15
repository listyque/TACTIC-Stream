"""Format portable JS with Qt's parser, which also executes these modules."""
import argparse
from pathlib import Path
import subprocess

import PySide6

ROOT = Path(__file__).resolve().parents[1]
FORMATTER = Path(PySide6.__file__).parent / "qmlformat.exe"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = []
    files = sorted((ROOT / "src/tactic_stream/shared_ui").rglob("*.mjs"))
    for path in files:
        result = subprocess.run([str(FORMATTER), "--newline", "unix", str(path)], capture_output=True, check=True)
        formatted = result.stdout.replace(b"\r\r\n", b"\n").replace(b"\r\n", b"\n")
        assert formatted.strip(), path
        if formatted != path.read_bytes():
            changed.append(str(path.relative_to(ROOT)))
            if not args.check:
                path.write_bytes(formatted)
    if args.check and changed:
        raise SystemExit("Unformatted Tactic Frame modules:\n" + "\n".join(changed))
    print(f"{'Checked' if args.check else 'Formatted'} {len(files)} modules; {len(changed)} changed")


if __name__ == "__main__":
    main()
