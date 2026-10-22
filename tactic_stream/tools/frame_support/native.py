"""Run actual native support surfaces from the independent Handler checkout."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path("D:/grav/Tactic Stream/TH")))
from tests.frame_support_fixture import Surface, SCREENS, evaluate, variant, main

if __name__ == "__main__":
    main()
