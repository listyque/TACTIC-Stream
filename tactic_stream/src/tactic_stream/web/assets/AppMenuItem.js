import { G as withCtx, M as openBlock, T as mergeProps, _ as createElementBlock, b as createVNode, et as unref, g as createCommentVNode, h as createBlock, m as createBaseVNode, rt as toDisplayString } from "./vue.js";
import { D as t, o as _sfc_main$1, u as _sfc_main$2 } from "./index.js";
//#region src/controls/AppMenuItem.vue
var _hoisted_1 = { class: "app-menu-item" };
var _hoisted_2 = { class: "app-menu-item-label" };
var _sfc_main = /*@__PURE__*/ Object.assign({ inheritAttrs: false }, {
	__name: "AppMenuItem",
	props: {
		label: String,
		icon: String,
		checked: {
			type: Boolean,
			default: void 0
		},
		disabled: Boolean,
		disabledReason: String,
		translate: {
			type: Boolean,
			default: true
		},
		secondaryLabel: String,
		secondaryIcon: {
			type: String,
			default: "close"
		}
	},
	emits: ["click", "secondary"],
	setup(__props, { emit: __emit }) {
		const emit = __emit;
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1, [createVNode(_sfc_main$1, mergeProps(_ctx.$attrs, {
				"data-menu-primary": "",
				icon: __props.icon,
				label: __props.label,
				"aria-label": __props.translate ? unref(t)(__props.label) : __props.label,
				title: __props.disabled && __props.disabledReason ? unref(t)(__props.disabledReason) : __props.translate ? unref(t)(__props.label) : __props.label,
				"aria-description": __props.disabled && __props.disabledReason ? unref(t)(__props.disabledReason) : void 0,
				role: __props.checked === void 0 ? "menuitem" : "menuitemradio",
				"aria-checked": __props.checked,
				disabled: __props.disabled,
				onClick: _cache[0] || (_cache[0] = ($event) => emit("click", $event))
			}), {
				default: withCtx(() => [createBaseVNode("span", _hoisted_2, toDisplayString(__props.translate ? unref(t)(__props.label) : __props.label), 1), __props.checked ? (openBlock(), createBlock(_sfc_main$2, {
					key: 0,
					name: "check-circle",
					class: "menu-check"
				})) : createCommentVNode("", true)]),
				_: 1
			}, 16, [
				"icon",
				"label",
				"aria-label",
				"title",
				"aria-description",
				"role",
				"aria-checked",
				"disabled"
			]), __props.secondaryLabel ? (openBlock(), createBlock(_sfc_main$1, {
				key: 0,
				"data-menu-secondary": "",
				"icon-only": "",
				icon: __props.secondaryIcon,
				label: __props.secondaryLabel,
				role: "menuitem",
				disabled: __props.disabled,
				onClick: _cache[1] || (_cache[1] = ($event) => emit("secondary", $event))
			}, null, 8, [
				"icon",
				"label",
				"disabled"
			])) : createCommentVNode("", true)]);
		};
	}
});
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppMenuItem.js.map