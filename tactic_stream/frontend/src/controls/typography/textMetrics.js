// Measure layout with design advances, independent of small-size font pixel rounding.
// Caret positioning and text clipping still measure their actual painted text.
let context;
function layoutContext(font) {
  context ||= document.createElement('canvas').getContext('2d');
  context.font = font.replace(
    /(\d+(?:\.\d+)?)px/,
    (_, size) => Number(size) * 64 + 'px'
  );
  return context;
}
export function layoutTextWidth(text, font) {
  return layoutContext(font).measureText(String(text)).width / 64;
}

export function qtLabelTextWidth(text, font) {
  const canvas = layoutContext(font),
    glyphs = [...String(text)];
  const widths = glyphs.map((glyph) => canvas.measureText(glyph).width);
  // shortcut: Qt fixed advances and pair kerning cover shipped Segoe UI EN/RU; other scripts need shaping.
  return widths.reduce((sum, width, index) => {
    const kerning = index
      ? canvas.measureText(glyphs[index - 1] + glyphs[index]).width -
        widths[index - 1] -
        width
      : 0;
    return sum + (Math.floor(width) + Math.round(kerning)) / 64;
  }, 0);
}
