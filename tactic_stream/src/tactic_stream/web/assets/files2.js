//#region src/controls/files.js
function downloadBlob(blob, filename) {
	const href = URL.createObjectURL(blob), link = document.createElement("a");
	link.href = href;
	link.download = filename;
	link.click();
	setTimeout(() => URL.revokeObjectURL(href), 1e3);
}
//#endregion
export { downloadBlob as t };

//# sourceMappingURL=files2.js.map