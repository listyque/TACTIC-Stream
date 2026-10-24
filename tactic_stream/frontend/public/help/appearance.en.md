---
group: Configuration
icon: palette
order: 35
---
# Appearance configuration

> Appearance controls the visual theme, semantic icon font, motion, interface language and browser
> presentation. Changes preview immediately; Apply/Save persists them.

## Appearance

| Setting | What it controls |
| --- | --- |
| **Dark color mode** | Uses dark surfaces and the dark palette assigned to the selected interface style. Turning it off uses the light palette. |
| **Interface style** | Selects the component styling rules. Each style remembers its own light and dark palettes. |
| **Light mode palette** | Base surface and accent used while dark mode is off. |
| **Dark mode palette** | Base surface and accent used while dark mode is on. |
| **Icon set** | Chooses the bundled semantic icon font. Material Design Icons is the default. Automatic follows the application's preferred set; the other options force a family. Material Design and Fluent glyphs are optically scaled to match Font Awesome without changing control geometry. Unknown dynamic icons still fall back to another bundled family instead of disappearing. |
| **Click animations** | Animates press feedback, ripples, switches, and disclosure controls. Disabled controls still change state, but without motion. |
| **Hover animations** | Animates pointer hover transitions. Hover states still appear immediately when disabled. |
| **Fades and transitions** | Animates appearing content, view changes, expansion, and other interface fades. |
| **Menu and popup animations** | Animates menus, combo boxes, popups, and tooltips. Disable it for instant opening and dismissal. |

Enabled interface animations use short durations across all styles: about 2.5 times faster than the previous motion timing. The switches above still disable their respective animations completely.

## Language

**Interface language** changes application labels and selects the matching help articles. Project
names, Search Types, processes, statuses, and other server-defined data are never translated.

Common interface messages use the same source-text translations as the current TACTIC Handler. Labels update in the existing window without discarding its draft; missing translations fall back to English. Stream-specific messages and Markdown help articles keep their own language resources.

## Browser preferences and preview

System color mode, standalone notes and icon preview remain visible additions. Palette tiles use the shared 36px control with an 18px accent circle. Theme/animation/language changes preview immediately while Configuration is open; Apply/Save persists them and discarding changes restores the last applied values. Close protects unsaved settings. The reduced-motion system preference takes priority. Graphics backend selection belongs to Qt; browser rendering is managed by the browser.


## Legacy template icons

Known icons from legacy templates are mapped to modern symbols in the shared icon catalogue. For example, PICTURE_EDIT uses an image, DETAILS a document, PHOTOS an image collection, FILM/MOVIE_VIEW a film and PLUGIN a puzzle piece. Old built-in PNG filenames and exact /context/icons/... references use the same mappings. The selected icon set still applies; an explicitly qualified font icon keeps its family. Project XML is preserved. This catalogue covers the shipped template references, not every historical IconWdg icon or custom plugin image. Unknown custom names, paths and remote images are not guessed from their labels. Restart Handler after installing the updated UI; reload the browser after updating Stream.
