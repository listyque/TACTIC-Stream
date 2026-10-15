import { E as mergeProps, N as openBlock, T as mergeModels, V as useModel, et as unref, h as createBaseVNode, v as createElementBlock } from "./vue.js";
import { T as t } from "./index.js";
//#region src/controls/AppSwitch.vue
var _hoisted_1 = { class: "switch-control" };
var _hoisted_2 = ["aria-label", "checked"];
var _sfc_main = /*@__PURE__*/ Object.assign({ inheritAttrs: false }, {
	__name: "AppSwitch",
	props: /*@__PURE__*/ mergeModels({ label: String }, {
		"modelValue": {
			type: Boolean,
			default: false
		},
		"modelModifiers": {}
	}),
	emits: ["update:modelValue"],
	setup(__props) {
		const model = useModel(__props, "modelValue");
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("label", _hoisted_1, [createBaseVNode("input", mergeProps(_ctx.$attrs, {
				class: "app-switch",
				type: "checkbox",
				role: "switch",
				"aria-label": __props.label ? unref(t)(__props.label) : void 0,
				checked: model.value,
				onChange: _cache[0] || (_cache[0] = ($event) => model.value = $event.target.checked)
			}), null, 16, _hoisted_2)]);
		};
	}
});
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppSwitch.js.map