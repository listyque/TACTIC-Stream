# Table comparison fixtures

- `legacy_inventory.json`: pinned original widget/class/config catalogue used by
  `../inventory.py` and `../../used_table_widgets.py`. This is an input baseline,
  not a claim about current implementation completeness.
- `comparison_scene.json`: explicit comparison data loaded by `../capture.py`.
- `native_table_metrics.json` and `native_completion_metrics.json`: pinned native
  geometry/color inputs for the browser table and widget-catalogue tests. They
  do not certify current native/browser parity.

These files were separated from historical report directories without changing
their bytes. Keep them versioned. New measurements, screenshots and generated
inventories belong under `../output/`, which is ignored by Git.
