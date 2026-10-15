# Bundled icon fonts

- Font Awesome 5 is retained for TACTIC sidebar compatibility. Its bundled
  files predate this catalog update.
  The three Font Awesome/MDI `*-charmap.json` files are copied unchanged from
  Handler `thlib/ui/assets/fonts`, matching these bundled fonts; used by the
  shared AppIcon to resolve configured sidebar glyph names.
- Material Design Icons 7.4.47 is from
  <https://github.com/Templarian/MaterialDesign-Webfont> and is distributed
  under the Apache License 2.0. See `MATERIAL_DESIGN_ICONS_LICENSE.txt`.
- Fluent System Icons Resizable is from Microsoft Fluent UI System Icons at
  commit `2e4da95009de778ae0f41ec6c17bc67c97f4dc56` and is distributed under
  the MIT License. See `FLUENT_SYSTEM_ICONS_LICENSE.txt`.
  Its `fluent-system-icons-resizable.json` is copied unchanged from Handler;
  canonical Regular/Filled names use the same `_20_` extraction as `icon_font.py`.
