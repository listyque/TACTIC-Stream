import { M as openBlock, _ as createElementBlock, et as unref, h as createBlock, nt as normalizeStyle, p as computed, tt as normalizeClass } from "./vue.js";
import { L as _plugin_vue_export_helper_default, o as t } from "./AppButton.js";
//#region ../src/tactic_stream/shared_ui/controls/display/progress.mjs
function fraction(value, minimum = 0, maximum = 1) {
	if (typeof value !== "number" || !isFinite(value)) return null;
	if (maximum <= minimum) return 0;
	return Math.max(0, Math.min(1, (value - minimum) / (maximum - minimum)));
}
//#endregion
//#region src/controls/AppProgress.vue
var _hoisted_1 = [
	"aria-label",
	"aria-valuemin",
	"aria-valuemax",
	"aria-valuenow"
];
var AppProgress_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "AppProgress",
	props: {
		label: String,
		value: Number,
		min: {
			type: Number,
			default: 0
		},
		max: {
			type: Number,
			default: 1
		}
	},
	setup(__props) {
		const props = __props;
		const position = computed(() => fraction(props.value, props.min, props.max));
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("span", {
				class: normalizeClass(["app-progress", { determinate: position.value !== null }]),
				role: "progressbar",
				"aria-label": unref(t)(__props.label),
				"aria-valuemin": position.value !== null ? __props.min : void 0,
				"aria-valuemax": position.value !== null ? __props.max : void 0,
				"aria-valuenow": position.value !== null ? Math.max(__props.min, Math.min(__props.max, __props.value)) : void 0,
				style: normalizeStyle({ "--progress-value": position.value })
			}, null, 14, _hoisted_1);
		};
	}
}, [["__scopeId", "data-v-079e775b"]]);
//#endregion
//#region src/frame/controls/display/FrameProgress.vue
var _sfc_main = {
	__name: "FrameProgress",
	props: { frameNode: Object },
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createBlock(AppProgress_default, {
				label: __props.frameNode.label,
				value: __props.frameNode.indeterminate ? void 0 : __props.frameNode.value,
				min: __props.frameNode.min,
				max: __props.frameNode.max
			}, null, 8, [
				"label",
				"value",
				"min",
				"max"
			]);
		};
	}
};
//#endregion
export { AppProgress_default as n, _sfc_main as t };

//# sourceMappingURL=FrameProgress.js.map