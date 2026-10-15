import { D as nextTick, H as watch, N as openBlock, X as ref, j as onMounted, k as onBeforeUnmount, rt as toDisplayString, v as createElementBlock } from "./vue.js";
//#region src/controls/MiddleElide.vue
var _hoisted_1 = ["title", "aria-label"];
var _sfc_main = {
	__name: "MiddleElide",
	props: { text: String },
	setup(__props) {
		const props = __props;
		const label = ref(null), displayed = ref(props.text || "");
		let observer, context;
		function measure() {
			if (!label.value || !context) return;
			const style = getComputedStyle(label.value), width = label.value.clientWidth;
			context.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
			const text = props.text || "";
			if (context.measureText(text).width <= width) {
				displayed.value = text;
				return;
			}
			const parts = Array.from(text), candidate = (length) => parts.slice(0, Math.ceil(length / 2)).join("") + "…" + parts.slice(parts.length - Math.floor(length / 2)).join("");
			let low = 0, high = parts.length;
			while (low < high) {
				const mid = Math.ceil((low + high) / 2);
				if (context.measureText(candidate(mid)).width <= width) low = mid;
				else high = mid - 1;
			}
			displayed.value = candidate(low);
		}
		onMounted(() => {
			context = document.createElement("canvas").getContext("2d");
			observer = new ResizeObserver(measure);
			observer.observe(label.value);
			document.fonts.ready.then(measure);
			measure();
		});
		onBeforeUnmount(() => observer?.disconnect());
		watch(() => props.text, () => nextTick(measure));
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("span", {
				ref_key: "label",
				ref: label,
				class: "middle-elide",
				title: __props.text,
				"aria-label": __props.text
			}, toDisplayString(displayed.value), 9, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=MiddleElide.js.map