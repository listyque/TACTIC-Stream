import { K as withDirectives, N as openBlock, X as ref, et as unref, m as computed, s as vModelText, v as createElementBlock } from "./vue.js";
import { D as t } from "./index.js";
//#region src/controls/AppTextField.vue
var _hoisted_1 = [
	"aria-invalid",
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
		disabled: Boolean,
		errorState: Boolean
	},
	emits: ["update:modelValue"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const text = computed({
			get: () => String(props.modelValue ?? ""),
			set: (value) => emit("update:modelValue", String(value))
		});
		const field = ref(null);
		__expose({ focus() {
			field.value?.focus();
		} });
		return (_ctx, _cache) => {
			return withDirectives((openBlock(), createElementBlock("input", {
				ref_key: "field",
				ref: field,
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => text.value = $event),
				class: "app-text-field",
				"aria-invalid": __props.errorState || void 0,
				"aria-label": __props.label || __props.placeholder ? unref(t)(__props.label || __props.placeholder) : void 0,
				placeholder: unref(t)(__props.placeholder || ""),
				disabled: __props.disabled
			}, null, 8, _hoisted_1)), [[vModelText, text.value]]);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppTextField.js.map