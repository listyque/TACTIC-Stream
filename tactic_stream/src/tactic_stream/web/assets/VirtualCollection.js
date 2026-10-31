import { A as onMounted, E as nextTick, H as watch, M as openBlock, N as renderList, O as onBeforeUnmount, P as renderSlot, X as ref, _ as createElementBlock, nt as normalizeStyle, p as computed, u as Fragment } from "./vue.js";
import { V as observeFrameSizes } from "./FrameView.js";
//#region ../src/tactic_stream/shared_ui/controls/lists/collection.mjs
function layout(items, width, options = {}) {
	const columns = Math.max(1, Math.floor((width + (options.columnGap || 0)) / ((options.cellWidth || width || 1) + (options.columnGap || 0)))), cellWidth = options.cellWidth ? Math.min(width, options.cellWidth) : width, rows = [], rowByKey = Object.create(null);
	let top = 0;
	for (let index = 0; index < items.length; index += columns) {
		const cells = items.slice(index, index + columns), height = Math.max(1, ...cells.map((item) => item.height));
		rows.push({
			top,
			height,
			entries: cells.map((item, column) => ({
				key: item.key,
				index: index + column,
				data: item.data,
				left: column * (cellWidth + (options.columnGap || 0)),
				width: cellWidth
			}))
		});
		for (const item of cells) rowByKey[item.key] = rows.length - 1;
		top += height + (options.rowGap || 0);
	}
	return {
		rows,
		rowByKey,
		height: rows.length ? top - (options.rowGap || 0) : 0
	};
}
function range(rows, top, height, overscan = 240) {
	function firstAfter(value) {
		let low = 0, high = rows.length;
		while (low < high) {
			const middle = low + high >> 1;
			if (rows[middle].top + rows[middle].height < value) low = middle + 1;
			else high = middle;
		}
		return low;
	}
	return [firstAfter(top - overscan), Math.min(rows.length, firstAfter(top + height + overscan) + 1)];
}
//#endregion
//#region src/controls/lists/VirtualCollection.vue
var _hoisted_1 = ["data-collection-total"];
var _hoisted_2 = [
	"aria-setsize",
	"aria-posinset",
	"data-collection-key"
];
var _sfc_main = {
	__name: "VirtualCollection",
	props: {
		items: Array,
		cellWidth: Number,
		columnGap: {
			type: Number,
			default: 0
		},
		rowGap: {
			type: Number,
			default: 0
		}
	},
	setup(__props) {
		const props = __props;
		const host = ref(null), width = ref(1), top = ref(0), height = ref(600), focused = ref(""), measurements = ref(/* @__PURE__ */ new Map());
		const geometry = computed(() => layout(props.items.map((item) => ({
			...item,
			height: measurements.value.get(item.key) || item.height
		})), width.value, props));
		const visible = computed(() => {
			const [first, last] = range(geometry.value.rows, top.value, height.value);
			const rows = geometry.value.rows.slice(first, last), focusRow = geometry.value.rowByKey[focused.value];
			if (focusRow != null && (focusRow < first || focusRow >= last)) rows.push(geometry.value.rows[focusRow]);
			return rows.flatMap((row) => row.entries.map((entry) => ({
				...entry,
				top: row.top
			})));
		});
		let observer, frame = 0;
		const scrollParents = [];
		function update() {
			frame = 0;
			if (!host.value) return;
			const bounds = host.value.getBoundingClientRect();
			let low = 0, high = innerHeight;
			for (const parent of scrollParents) {
				const rect = parent.getBoundingClientRect();
				low = Math.max(low, rect.top + parent.clientTop);
				high = Math.min(high, rect.top + parent.clientTop + parent.clientHeight);
			}
			top.value = low - bounds.top;
			height.value = Math.max(0, high - low);
			width.value = host.value.clientWidth;
		}
		function schedule() {
			if (!frame) frame = requestAnimationFrame(update);
		}
		const elements = /* @__PURE__ */ new Map();
		function measure(element, key) {
			const previous = elements.get(key);
			if (previous === element) return;
			if (previous) observer?.unobserve(previous);
			if (element) {
				elements.set(key, element);
				observer?.observe(element);
			} else elements.delete(key);
		}
		function focus(event) {
			focused.value = host.value?.contains(event.target) ? event.target.closest("[data-collection-key]")?.dataset.collectionKey || "" : "";
		}
		async function navigate(event) {
			if (![
				"ArrowUp",
				"ArrowDown",
				"Home",
				"End"
			].includes(event.key) || !event.target.matches("article[tabindex]")) return;
			const current = props.items.findIndex((item) => item.key === event.target.closest("[data-collection-key]")?.dataset.collectionKey), columns = geometry.value.rows[0]?.entries.length || 1, target = event.key === "Home" ? 0 : event.key === "End" ? props.items.length - 1 : Math.max(0, Math.min(props.items.length - 1, current + (event.key === "ArrowUp" ? -columns : columns)));
			if (current < 0) return;
			event.preventDefault();
			focused.value = props.items[target].key;
			await nextTick();
			const element = elements.get(focused.value);
			element?.scrollIntoView({ block: "nearest" });
			element?.querySelector("article[tabindex]")?.focus({ preventScroll: true });
		}
		watch(() => [props.cellWidth, props.items], ([cellWidth, items], previous) => {
			if (cellWidth !== previous?.[0]) measurements.value = /* @__PURE__ */ new Map();
			else {
				const keys = new Set(items.map((item) => item.key));
				if ([...measurements.value.keys()].some((key) => !keys.has(key))) measurements.value = new Map([...measurements.value].filter(([key]) => keys.has(key)));
			}
			nextTick(schedule);
		});
		onMounted(() => {
			for (let parent = host.value.parentElement; parent; parent = parent.parentElement) if (/(auto|scroll)/.test(getComputedStyle(parent).overflowY)) {
				scrollParents.push(parent);
				parent.addEventListener("scroll", schedule, { passive: true });
			}
			observer = observeFrameSizes((entries) => {
				const sizes = new Map(measurements.value);
				let changed = false;
				for (const entry of entries) {
					if (entry.target === host.value || scrollParents.includes(entry.target)) {
						schedule();
						continue;
					}
					const key = entry.target.dataset.collectionKey, measured = Math.ceil(entry.borderBoxSize?.[0]?.blockSize || entry.target.getBoundingClientRect().height);
					if (key && measured > 0 && sizes.get(key) !== measured) {
						sizes.set(key, measured);
						changed = true;
					}
				}
				if (changed) measurements.value = sizes;
			});
			observer.observe(host.value);
			for (const parent of scrollParents) observer.observe(parent);
			for (const element of elements.values()) observer.observe(element);
			window.addEventListener("resize", schedule);
			window.addEventListener("scroll", schedule, { passive: true });
			document.addEventListener("focusin", focus);
			update();
		});
		onBeforeUnmount(() => {
			cancelAnimationFrame(frame);
			observer?.disconnect();
			for (const parent of scrollParents) parent.removeEventListener("scroll", schedule);
			window.removeEventListener("resize", schedule);
			window.removeEventListener("scroll", schedule);
			document.removeEventListener("focusin", focus);
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "virtual-collection",
				role: "list",
				style: normalizeStyle({ height: geometry.value.height + "px" }),
				"data-collection-total": __props.items.length,
				onKeydown: navigate
			}, [(openBlock(true), createElementBlock(Fragment, null, renderList(visible.value, (entry) => {
				return openBlock(), createElementBlock("div", {
					key: entry.key,
					ref_for: true,
					ref: (element) => measure(element, entry.key),
					class: "virtual-collection-entry",
					role: "listitem",
					"aria-setsize": __props.items.length,
					"aria-posinset": entry.index + 1,
					"data-collection-key": entry.key,
					style: normalizeStyle({
						left: entry.left + "px",
						top: entry.top + "px",
						width: entry.width + "px"
					})
				}, [renderSlot(_ctx.$slots, "default", {
					item: entry.data,
					index: entry.index
				})], 12, _hoisted_2);
			}), 128))], 44, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=VirtualCollection.js.map