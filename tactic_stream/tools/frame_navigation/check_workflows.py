"""Exercise navigation/project/tab/session flows on a private disposable server."""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "output"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "tests")]
    os.environ.update(
        TMP=str(ROOT / ".tmp/frame-tests"), TEMP=str(ROOT / ".tmp/frame-tests")
    )
    from test_transport import Transport
    from pyasm.security.authenticator import hash_password

    Transport.setUpClass()
    fixture = Transport()
    try:
        fixture._workspace_schema_fixture()
        with fixture.proxy() as proxy:
            auth = dict(
                ticket=proxy.get_ticket("admin", "private-test-password"), project="one"
            )
            proxy.insert(
                auth,
                "sthpw/login",
                dict(
                    login="workspace_user",
                    password=hash_password("private-test-password"),
                ),
            )
            proxy.insert(
                auth,
                "sthpw/login_group",
                dict(
                    code="frame_workspace_reader",
                    login_group="frame_workspace_reader",
                    access_level="low",
                    access_rules='<rules><rule group="project" code="one" access="allow"/><rule group="project" key="one" access="allow"/><rule group="project" code="two" access="allow"/><rule group="project" key="two" access="allow"/><rule group="search_type" code="*" access="allow"/></rules>',
                ),
            )
            proxy.insert(
                auth,
                "sthpw/login_in_group",
                dict(login="workspace_user", login_group="frame_workspace_reader"),
            )
        environment = dict(
            os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / ".browser-cache")
        )
        for name in (
            "navigation",
            "workspace_session",
            "session_expiry",
            "workspace_lifecycle",
        ):
            with (OUT / (name + ".log")).open("w", encoding="utf-8") as log:
                result = subprocess.run(
                    ["node", "tests/" + name + ".mjs", Transport.url],
                    cwd=ROOT / "frontend",
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=100,
                )
            assert result.returncode == 0, f"{name}: see {OUT / (name + '.log')}"
            print(name, "passed", flush=True)
    finally:
        fixture.doCleanups()
        Transport.tearDownClass()


if __name__ == "__main__":
    main()
