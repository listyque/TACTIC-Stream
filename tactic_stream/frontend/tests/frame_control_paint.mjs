// Read actual painted text, including input placeholders, rather than declarations.
export async function textMetrics(page) {
  return page.locator('[data-frame="sample"]').evaluate((root) => {
    const context = document.createElement('canvas').getContext('2d');
    const viewport = root.getBoundingClientRect();
    return [root, ...root.querySelectorAll('*')].flatMap((element) => {
      if (!element.checkVisibility() || element.closest('option')) return [];
      const box = element.getBoundingClientRect();
      if (
        !box.width ||
        !box.height ||
        box.bottom <= viewport.top ||
        box.top >= viewport.bottom ||
        box.right <= viewport.left ||
        box.left >= viewport.right
      )
        return [];
      const layout = getComputedStyle(element);
      let css = layout,
        text,
        painted;
      const input = element.matches(
        'input:not([type=range]):not([type=checkbox]):not([type=file]),textarea,select'
      );
      if (input) {
        text =
          element.tagName === 'SELECT'
            ? element.selectedOptions[0]?.textContent
            : element.value || element.placeholder;
        if (!element.value && element.placeholder)
          css = getComputedStyle(element, '::placeholder');
      } else {
        const nodes = [...element.childNodes].filter(
          (child) =>
            child.nodeType === Node.TEXT_NODE && child.textContent.trim()
        );
        if (!nodes.length) return [];
        text = nodes.map((child) => child.textContent).join('');
        const range = document.createRange();
        range.setStartBefore(nodes[0]);
        range.setEndAfter(nodes.at(-1));
        painted = range.getClientRects()[0];
      }
      if (!text?.trim()) return [];
      context.font = `${css.fontWeight} ${parseFloat(css.fontSize) * 64}px ${css.fontFamily}`;
      const scaled = context.measureText(text);
      const metrics = { width: scaled.width / 64 };
      const ascent = scaled.fontBoundingBoxAscent / 64,
        descent = scaled.fontBoundingBoxDescent / 64;
      const left =
        parseFloat(layout.borderLeftWidth) + parseFloat(layout.paddingLeft);
      const top =
        parseFloat(layout.borderTopWidth) + parseFloat(layout.paddingTop);
      const bottom =
        parseFloat(layout.borderBottomWidth) + parseFloat(layout.paddingBottom);
      const right =
        parseFloat(layout.borderRightWidth) + parseFloat(layout.paddingRight);
      const x = input
        ? box.x +
          left +
          (layout.textAlign === 'center'
            ? (box.width - left - right - metrics.width) / 2
            : 0)
        : (painted?.x ?? box.x);
      const baseline = input
        ? element.tagName === 'TEXTAREA'
          ? box.y + top + ascent - element.scrollTop
          : box.y +
            top +
            (box.height - top - bottom - ascent - descent) / 2 +
            ascent
        : (painted?.y ?? box.y) +
          ((painted?.height ?? box.height) - ascent - descent) / 2 +
          ascent;
      return [
        {
          text: text.trim(),
          x,
          baseline,
          advance: painted?.width ?? metrics.width,
          width: box.width,
          height: box.height,
          fontSize: parseFloat(css.fontSize),
          weight: Number(css.fontWeight),
          family: css.fontFamily,
          color: css.color
        }
      ];
    });
  });
}
