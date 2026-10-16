// Measure layout with design advances, independent of small-size font pixel rounding.
// Caret positioning and text clipping still measure their actual painted text.
let context;
export function layoutTextWidth(text, font) {
  context ||= document.createElement('canvas').getContext('2d');
  context.font = font.replace(
    /(\d+(?:\.\d+)?)px/,
    (_, size) => Number(size) * 64 + 'px'
  );
  return context.measureText(String(text)).width / 64;
}
