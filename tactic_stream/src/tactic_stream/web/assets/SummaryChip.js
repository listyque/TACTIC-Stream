import { G as withCtx, L as resolveDynamicComponent, M as openBlock, _ as createElementBlock, g as createCommentVNode, h as createBlock, m as createBaseVNode, nt as normalizeStyle, rt as toDisplayString, tt as normalizeClass } from "./vue.js";
import { o as _sfc_main$1, u as _sfc_main$2 } from "./index.js";
//#region src/controls/SummaryChip.vue
var _hoisted_1 = { key: 1 };
var _hoisted_2 = { key: 2 };
var _sfc_main = {
	__name: "SummaryChip",
	props: {
		label: String,
		count: Number,
		accent: String,
		icon: String,
		compact: Boolean,
		clickable: Boolean,
		showDot: {
			type: Boolean,
			default: true
		},
		showCount: {
			type: Boolean,
			default: true
		}
	},
	emits: ["click"],
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createBlock(resolveDynamicComponent(__props.clickable ? _sfc_main$1 : "div"), {
				class: normalizeClass(["summary-chip", {
					clickable: __props.clickable,
					compact: __props.compact
				}]),
				label: __props.clickable ? __props.label + (__props.showCount && __props.count != null ? " " + __props.count : "") : void 0,
				style: normalizeStyle({ "--chip-accent": __props.accent || "var(--primary)" }),
				onClick: _cache[0] || (_cache[0] = ($event) => __props.clickable && _ctx.$emit("click"))
			}, {
				default: withCtx(() => [
					__props.icon ? (openBlock(), createBlock(_sfc_main$2, {
						key: 0,
						name: __props.icon
					}, null, 8, ["name"])) : createCommentVNode("", true),
					__props.showDot ? (openBlock(), createElementBlock("i", _hoisted_1)) : createCommentVNode("", true),
					createBaseVNode("span", null, toDisplayString(__props.label), 1),
					__props.showCount ? (openBlock(), createElementBlock("small", _hoisted_2, toDisplayString(__props.count), 1)) : createCommentVNode("", true)
				]),
				_: 1
			}, 8, [
				"class",
				"label",
				"style"
			]);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=SummaryChip.js.map