import { F as renderSlot, N as openBlock, T as mergeModels, V as useModel, _ as createCommentVNode, b as createTextVNode, et as unref, g as createBlock, h as createBaseVNode, rt as toDisplayString, tt as normalizeClass, v as createElementBlock } from "./vue.js";
import { D as t, u as _sfc_main$1 } from "./index.js";
//#region src/controls/AppCheckbox.vue
var _hoisted_1 = { class: "app-checkbox-indicator" };
var _hoisted_2 = [
	"id",
	"checked",
	"disabled",
	"indeterminate",
	"aria-label"
];
var _sfc_main = {
	__name: "AppCheckbox",
	props: /*@__PURE__*/ mergeModels({
		label: String,
		controlId: String,
		disabled: Boolean,
		indeterminate: Boolean,
		compact: Boolean,
		hideLabel: Boolean,
		translateLabel: {
			type: Boolean,
			default: true
		}
	}, {
		"modelValue": {
			type: Boolean,
			default: false
		},
		"modelModifiers": {}
	}),
	emits: /*@__PURE__*/ mergeModels(["update:modelValue"], ["update:modelValue"]),
	setup(__props, { emit: __emit }) {
		const props = __props;
		const model = useModel(__props, "modelValue");
		const emit = __emit;
		function changed(event) {
			if (props.indeterminate) emit("update:modelValue", true);
			else model.value = event.target.checked;
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("label", { class: normalizeClass(["app-checkbox", {
				disabled: __props.disabled,
				compact: __props.compact
			}]) }, [createBaseVNode("span", _hoisted_1, [createBaseVNode("input", {
				id: __props.controlId,
				type: "checkbox",
				checked: !__props.indeterminate && model.value,
				onChange: changed,
				disabled: __props.disabled,
				indeterminate: __props.indeterminate,
				"aria-label": __props.label ? __props.translateLabel ? unref(t)(__props.label) : __props.label : void 0
			}, null, 40, _hoisted_2), model.value || __props.indeterminate ? (openBlock(), createBlock(_sfc_main$1, {
				key: 0,
				name: __props.indeterminate ? "minus" : "check"
			}, null, 8, ["name"])) : createCommentVNode("", true)]), !__props.hideLabel ? renderSlot(_ctx.$slots, "default", {}, () => [createTextVNode(toDisplayString(__props.label ? __props.translateLabel ? unref(t)(__props.label) : __props.label : ""), 1)], void 0, 0) : createCommentVNode("", true)], 2);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppCheckbox.js.map