//#region src/controls/typography/textMetrics.js
var context;
function layoutContext(font) {
	context ||= document.createElement("canvas").getContext("2d");
	context.font = font.replace(/(\d+(?:\.\d+)?)px/, (_, size) => Number(size) * 64 + "px");
	return context;
}
function layoutTextWidth(text, font) {
	return layoutContext(font).measureText(String(text)).width / 64;
}
function qtLabelTextWidth(text, font) {
	const canvas = layoutContext(font), glyphs = [...String(text)];
	const widths = glyphs.map((glyph) => canvas.measureText(glyph).width);
	return widths.reduce((sum, width, index) => {
		const kerning = index ? canvas.measureText(glyphs[index - 1] + glyphs[index]).width - widths[index - 1] - width : 0;
		return sum + (Math.floor(width) + Math.round(kerning)) / 64;
	}, 0);
}
//#endregion
export { qtLabelTextWidth as n, layoutTextWidth as t };

//# sourceMappingURL=textMetrics.js.map