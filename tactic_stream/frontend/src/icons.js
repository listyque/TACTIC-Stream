import materialMap from './assets/fonts/materialdesignicons-webfont-charmap.json';
import solidMap from './assets/fonts/fontawesome5-solid-webfont-charmap.json';
import regularMap from './assets/fonts/fontawesome5-regular-webfont-charmap.json';
import fluentMap from './assets/fonts/fluent-system-icons-resizable.json';
import {
  resolve as resolveSemanticIcon,
  ownValue
} from '../../src/tactic_stream/shared_ui/core/icons.mjs';

export const iconMaps = {
  'material-design': materialMap,
  'fontawesome-solid': solidMap,
  'fontawesome-outline': regularMap,
  'fluent-regular': {},
  'fluent-filled': {}
};
for (const [name, code] of Object.entries(fluentMap)) {
  const match = /^ic_fluent_(.+)_20_(regular|filled)$/.exec(name);
  if (match)
    iconMaps['fluent-' + match[2]][match[1].replaceAll('_', '-')] = code;
}
const iconCode = (code) =>
  String.fromCodePoint(typeof code === 'number' ? code : parseInt(code, 16));

// Both renderers choose the family and glyph through the same Frame policy.
export function resolveIcon(name, pack) {
  const selected = resolveSemanticIcon(name, pack, (family, glyph) =>
    ownValue(ownValue(iconMaps, family), glyph)
  );
  return selected
    ? [selected.set, iconCode(iconMaps[selected.set][selected.name])]
    : undefined;
}
