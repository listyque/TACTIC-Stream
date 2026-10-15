import { F as renderSlot, N as openBlock, _ as createCommentVNode, nt as normalizeStyle, tt as normalizeClass, v as createElementBlock } from "./vue.js";
//#region src/controls/ItemSurface.vue
var _hoisted_1 = {
	key: 0,
	class: "item-surface-rail",
	"aria-hidden": "true"
};
var _sfc_main = {
	__name: "ItemSurface",
	props: {
		accent: String,
		selected: Boolean,
		cornerRadius: {
			type: Number,
			default: 10
		},
		inset: {
			type: Number,
			default: 1
		},
		normalColor: String,
		selectedColor: String,
		railVisible: {
			type: Boolean,
			default: true
		},
		separatorVisible: {
			type: Boolean,
			default: true
		}
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: normalizeClass(["item-surface", {
					selected: __props.selected,
					"without-separator": !__props.separatorVisible
				}]),
				style: normalizeStyle({
					"--item-base": (__props.selected ? __props.selectedColor : __props.normalColor) || void 0,
					"--item-accent": __props.accent || "var(--primary)",
					"--item-corner": __props.cornerRadius + "px",
					"--item-inset": __props.inset + "px"
				})
			}, [__props.railVisible ? (openBlock(), createElementBlock("span", _hoisted_1)) : createCommentVNode("", true), renderSlot(_ctx.$slots, "default")], 6);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=ItemSurface.js.map