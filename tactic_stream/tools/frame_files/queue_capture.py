"""Populate the real queue owner without changing production settings or files."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock
import tempfile

from tests.test_commit_queue import payload
from tests.test_frame_queue import Screenshot
from thlib.ui.commit_queue import CommitQueueController
from thlib.ui.repository_sync import RepositorySyncController, PreparedSyncEntry
from thlib.ui.editor_tools import ScreenshotController
from tests.test_screenshot_controller import _WindowModel
from tests.test_frame_sync import Application, LocalFile
import tests.test_repository_sync_editor as editor_fixtures


def prepare(fixture, screen):
    fixture.enter_context(
        patch("thlib.ui.commit_queue.env_read_config", return_value={})
    )
    fixture.enter_context(patch("thlib.ui.commit_queue.env_write_config"))
    fixture.enter_context(
        patch("thlib.environment.env_tactic.get_all_base_dirs", return_value=[])
    )
    folder = Path(
        fixture.enter_context(tempfile.TemporaryDirectory(prefix="frame-queue-"))
    )
    owner = CommitQueueController()
    owner.set_auto_clean(False)
    fixture.callback(owner.shutdown)
    rows = []
    if screen != "queue-empty":
        for index in range(2):
            name = f"source_{index}.txt"
            path = folder / name
            path.write_text("queue input", encoding="utf-8")
            with patch(
                "thlib.ui.commit_queue.uuid.uuid4",
                return_value=SimpleNamespace(hex=str(index + 1)),
            ):
                operation_id = owner.add_prepared(payload(path), f"Asset {index}")
            owner._set_record(
                operation_id,
                versionedPaths=["repo/v001/" + name],
                versionlessPaths=["repo/latest/" + name],
                futureFileName=name,
            )
            rows.append(
                dict(
                    name=name,
                    title=f"Asset {index}",
                    files=[name],
                    context="publish",
                    process="publish",
                    version=0,
                    description="",
                )
            )
        owner.select_row(0)
    owner.set_advanced_options_expanded(screen == "queue-advanced")
    screenshot = Screenshot()
    return owner, screenshot, rows


def prepare_sync(fixture, screen):
    fixture.enter_context(patch("thlib.environment.env_read_config", return_value={}))
    fixture.enter_context(patch("thlib.environment.env_write_config"))
    fixture.enter_context(
        patch("thlib.environment.cfg_controls.get_checkin", return_value={})
    )
    owner = RepositorySyncController()
    fixture.callback(owner.shutdown)
    application = Application()
    context = dict(
        repositorySync=owner, repoSyncModel=owner.model, appController=application
    )
    if screen == "sync-editor":
        editor, requests = editor_fixtures.RepositorySyncEditorTests().make_controller()
        editor.presets.replace([{"name": "default", "title": "Default", "data": {}}])
        editor.select_preset(0)
        context.update(
            repositorySyncEditorController=editor,
            repositorySyncPresetModel=editor.presets,
            repositorySyncTreeModel=editor.model,
        )
        # Keep the fixture's domain collaborators alive with the real QObject owner.
        fixture.callback(lambda: (editor, requests, application))
    else:
        folder = Path(
            fixture.enter_context(tempfile.TemporaryDirectory(prefix="frame-sync-"))
        )
        for name in ("robot.ma", "diffuse.png", "preview.jpg"):
            path = folder / name
            owner._schedule_prepared_entry(
                PreparedSyncEntry(
                    file_object=LocalFile(path),
                    process="publish",
                    local_path=str(path),
                    web_path="http://127.0.0.1/not-started/" + name,
                    title=name,
                    expected_size=4096,
                    expected_md5="",
                )
            )
    return context


def prepare_screenshot(fixture):
    owner = ScreenshotController(Mock(), Mock())
    owner.prepare_for_operation("capture-fixture")
    fixture.callback(owner.shutdown)
    return dict(screenshotController=owner, windowModel=_WindowModel())
