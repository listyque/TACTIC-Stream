"""Inventory includes real declarations and registries, excluding quoted examples."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.frame_foundation import inventory


class FrameInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=inventory.ROOT / ".tmp")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_qml_aliases_comments_registry_and_docks(self):
        prefix = "thlib/ui/qml/"
        self.write(prefix + "MyPopup.qml", "import QtQuick\nPopup { id: popup }")
        self.write(prefix + "qmldir", "LocalPopup 1.0 MyPopup.qml\n")
        self.write(
            prefix + "Screen.qml",
            """Item {
            // Window { fake }
            property string example: "Menu { not_a_control }"
            LocalPopup { id: real }
        }""",
        )
        self.write(
            prefix + "shell/docks/DockContentRegistry.qml",
            """Item {
            readonly property Component notes: body
            Component { id: body
                Screen { }
            }
        }""",
        )
        self.write(
            "thlib/ui/workspace_models/windows.py",
            """class FloatingWindowModel:
            _content_sources = {'screen': 'Screen.qml'}
            _configuration_pages = frozenset({'appearance'})
        """,
        )
        data = inventory.native_inventory(self.root)
        self.assertEqual(len(data["surfaces"]), 2)
        self.assertEqual(data["windows"][0]["file"], prefix + "Screen.qml")
        self.assertEqual(data["docks"][0]["component"], "Screen")
        self.assertEqual(data["configuration"][0]["kind"], "appearance")
        self.write(
            "thlib/ui/workspace_models/windows.py",
            """class FloatingWindowModel:
            _content_sources = {'missing': 'Absent.qml'}
            _configuration_pages = frozenset()
        """,
        )
        with self.assertRaisesRegex(AssertionError, "Missing registered window"):
            inventory.native_inventory(self.root)

    def test_vue_ast_ignores_comment_and_retains_window_kind_and_line(self):
        source = """<template>
          <!-- <dialog>fake</dialog> -->
          <dialog ref="help" v-window="{ kind: 'help' }"><AppMenu /></dialog>
        </template>"""
        self.write("frontend/src/Help.vue", source)
        self.write(
            "frontend/src/features/workspace/docks.js",
            "export const dockPanels = [{id: 'results', title: 'Results', closable: false}]",
        )
        result = subprocess.run(
            ["node", str(inventory.HERE / "inventory_web.mjs"), str(self.root)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        data = json.loads(result.stdout)
        self.assertEqual(len(data["surfaces"]), 2)
        dialog = data["surfaces"][0]
        self.assertEqual(dialog["kind"], "help")
        self.assertEqual(dialog["line"], 3)
        self.assertEqual(data["docks"][0]["id"], "results")


if __name__ == "__main__":
    unittest.main()
