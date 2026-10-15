//#region src/frame/resize.js
function observeFrameSizes(apply) {
	const pending = /* @__PURE__ */ new Map();
	let frame = 0;
	let disconnected = false;
	const observer = new ResizeObserver((entries) => {
		if (disconnected) return;
		for (const entry of entries) pending.set(entry.target, entry);
		if (frame) return;
		frame = requestAnimationFrame(() => {
			frame = 0;
			const entries = [...pending.values()];
			pending.clear();
			if (!disconnected && entries.length) apply(entries);
		});
	});
	return {
		observe(target) {
			if (!disconnected) observer.observe(target);
		},
		unobserve(target) {
			pending.delete(target);
			observer.unobserve(target);
		},
		disconnect() {
			disconnected = true;
			observer.disconnect();
			cancelAnimationFrame(frame);
			frame = 0;
			pending.clear();
		}
	};
}
//#endregion
export { observeFrameSizes as t };

//# sourceMappingURL=resize.js.map