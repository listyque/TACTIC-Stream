# Studio Review

A full native TACTIC plugin for an existing business project, not a dashboard.

1. Run `python TS/examples/studio_review/build.py` from the workspace.
2. Administration → Plugins → Install a package: upload
   `TS/releases/studio-review-1.0.0.zip`, inspect its files and activate in a test project.
3. Open Studio Review from the sidebar. Its status/progress column uses the
   portable `studio_review.column` widget. `studio_review.widget` embeds it as a
   reusable item layout; open Resources → Saved preview to inspect it.
4. Resources → studio_review.theme: save edits and apply to the project.
   Personal light/dark mode remains available; Use personal appearance resets it.
5. Resources → approve: enter `{"review_code":"STUDIO_REVIEW_001"}`, run and
   confirm. It updates the actual review through native Search/SObject APIs.
6. Export ZIP to retain resource/data edits, reload to exercise reinstallation,
   then remove from the test project. Removal deletes this plugin's table and
   manifest-selected configurations and removes its sidebar link.

The package owns `studio/review` (`studio_review` table), `studio_review.*`
widget configurations, the `plugins/studio_review/approve` script,
`studio_review/installed` setting and `studio_review` sidebar entry. Choose another
namespace before adapting it for a project that already uses these identifiers.
It does not automatically select its theme or modify existing business types.

`build.py` deterministically creates ordinary SPT registration/data files and a
ZIP using the standard library. The installed package uses the native installer,
Command, schema/file journals and PythonCmd. The install/remove hooks manage only
its own setting/navigation. Export from the manager captures installed resource
and data edits; rerunning this example builder restores the original sample.

Server Python is trusted administrator code. Supply dependencies in the server
environment. Modern visual extensions use existing Frame controls and XML;
there is no WebView or dynamic QML/Vue compilation.
