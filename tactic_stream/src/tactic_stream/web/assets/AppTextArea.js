import { B as useModel, K as withDirectives, M as openBlock, X as ref, _ as createElementBlock, et as unref, o as vModelText, w as mergeModels } from "./vue.js";
import { D as t } from "./index.js";
//#region src/controls/AppTextArea.vue
var _hoisted_1 = [
	"aria-invalid",
	"aria-label",
	"placeholder",
	"disabled"
];
var _sfc_main = {
	__name: "AppTextArea",
	props: /*@__PURE__*/ mergeModels({
		label: String,
		placeholder: String,
		disabled: Boolean,
		errorState: Boolean
	}, {
		"modelValue": {
			type: String,
			default: ""
		},
		"modelModifiers": {}
	}),
	emits: ["update:modelValue"],
	setup(__props, { expose: __expose }) {
		const model = useModel(__props, "modelValue");
		const field = ref(null);
		__expose({ focus() {
			field.value?.focus();
		} });
		return (_ctx, _cache) => {
			return withDirectives((openBlock(), createElementBlock("textarea", {
				ref_key: "field",
				ref: field,
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => model.value = $event),
				class: "app-text-area",
				"aria-invalid": __props.errorState || void 0,
				"aria-label": unref(t)(__props.label || __props.placeholder),
				placeholder: unref(t)(__props.placeholder || ""),
				disabled: __props.disabled
			}, null, 8, _hoisted_1)), [[vModelText, model.value]]);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppTextArea.js.map