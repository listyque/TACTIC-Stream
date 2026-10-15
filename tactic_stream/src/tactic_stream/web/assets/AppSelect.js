import { G as withCtx, K as withDirectives, N as openBlock, P as renderList, R as resolveDynamicComponent, T as mergeModels, V as useModel, _ as createCommentVNode, d as Fragment, et as unref, g as createBlock, h as createBaseVNode, m as computed, nt as normalizeStyle, o as vModelSelect, rt as toDisplayString, v as createElementBlock, x as createVNode } from "./vue.js";
import { D as t, u as _sfc_main$1 } from "./index.js";
//#region src/controls/AppSelect.vue
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = {
	key: 0,
	type: "button",
	class: "app-select-trigger"
};
var _hoisted_3 = ["value"];
var _hoisted_4 = { class: "app-select-option-label" };
var _sfc_main = {
	__name: "AppSelect",
	props: /*@__PURE__*/ mergeModels({
		options: {
			type: Array,
			default: () => []
		},
		label: String,
		swatchMode: String,
		translateLabels: {
			type: Boolean,
			default: true
		}
	}, {
		"modelValue": {},
		"modelModifiers": {}
	}),
	emits: ["update:modelValue"],
	setup(__props) {
		const props = __props;
		const model = useModel(__props, "modelValue");
		const customizable = CSS.supports("appearance", "base-select");
		const decorated = computed(() => customizable && props.options.some((item) => item.icon));
		return (_ctx, _cache) => {
			return withDirectives((openBlock(), createElementBlock("select", {
				class: "app-select",
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => model.value = $event),
				"aria-label": __props.label ? unref(t)(__props.label) : void 0
			}, [
				unref(customizable) ? (openBlock(), createElementBlock("button", _hoisted_2, [(openBlock(), createBlock(resolveDynamicComponent("selectedcontent"))), createVNode(_sfc_main$1, {
					name: "expand_more",
					class: "app-select-indicator"
				})])) : createCommentVNode("", true),
				model.value !== void 0 && !__props.options.some((item) => item.value === model.value) ? (openBlock(), createElementBlock("option", {
					key: 1,
					value: model.value
				}, toDisplayString(model.value), 9, _hoisted_3)) : createCommentVNode("", true),
				(openBlock(true), createElementBlock(Fragment, null, renderList(__props.options, (item) => {
					return openBlock(), createBlock(resolveDynamicComponent("option"), {
						key: item.value,
						value: item.value,
						disabled: item.disabled
					}, {
						default: withCtx(() => [
							decorated.value && item.icon ? (openBlock(), createBlock(_sfc_main$1, {
								key: 0,
								name: item.icon
							}, null, 8, ["name"])) : createCommentVNode("", true),
							__props.swatchMode ? (openBlock(), createElementBlock("span", {
								key: 1,
								class: "palette-swatch",
								style: normalizeStyle({
									backgroundColor: item[__props.swatchMode],
									borderColor: item[__props.swatchMode + "Base"]
								})
							}, null, 4)) : createCommentVNode("", true),
							createBaseVNode("span", _hoisted_4, toDisplayString(__props.translateLabels ? unref(t)(item.label) : item.label), 1)
						]),
						_: 2
					}, 1032, ["value", "disabled"]);
				}), 128))
			], 8, _hoisted_1)), [[vModelSelect, model.value]]);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppSelect.js.map