import { N as openBlock, X as ref, et as unref, v as createElementBlock } from "./vue.js";
import { T as t } from "./index.js";
//#region src/controls/AppTextField.vue
var _hoisted_1 = [
	"value",
	"aria-label",
	"placeholder",
	"disabled"
];
var _sfc_main = {
	__name: "AppTextField",
	props: {
		modelValue: {
			type: [String, Number],
			default: ""
		},
		label: String,
		placeholder: String,
		disabled: Boolean
	},
	emits: ["update:modelValue"],
	setup(__props, { expose: __expose }) {
		const field = ref(null);
		__expose({ focus() {
			field.value?.focus();
		} });
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("input", {
				ref_key: "field",
				ref: field,
				class: "app-text-field",
				value: __props.modelValue,
				"aria-label": __props.label || __props.placeholder ? unref(t)(__props.label || __props.placeholder) : void 0,
				placeholder: unref(t)(__props.placeholder || ""),
				disabled: __props.disabled,
				onInput: _cache[0] || (_cache[0] = ($event) => _ctx.$emit("update:modelValue", $event.target.value))
			}, null, 40, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppTextField.js.map