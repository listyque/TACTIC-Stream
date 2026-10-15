import { K as withDirectives, N as openBlock, T as mergeModels, V as useModel, et as unref, nt as normalizeStyle, s as vModelText, v as createElementBlock } from "./vue.js";
import { D as t } from "./index.js";
//#region src/controls/AppSlider.vue
var _hoisted_1 = [
	"aria-label",
	"disabled",
	"min",
	"max",
	"step"
];
var _sfc_main = {
	__name: "AppSlider",
	props: /*@__PURE__*/ mergeModels({
		label: String,
		disabled: Boolean,
		min: {
			type: Number,
			default: 0
		},
		max: {
			type: Number,
			default: 100
		},
		step: {
			type: Number,
			default: 5
		}
	}, {
		"modelValue": {
			type: Number,
			default: 0
		},
		"modelModifiers": {}
	}),
	emits: ["update:modelValue"],
	setup(__props) {
		const model = useModel(__props, "modelValue");
		return (_ctx, _cache) => {
			return withDirectives((openBlock(), createElementBlock("input", {
				class: "app-slider",
				type: "range",
				"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => model.value = $event),
				style: normalizeStyle({ "--slider-position": (model.value - __props.min) / (__props.max - __props.min) * 100 + "%" }),
				"aria-label": unref(t)(__props.label),
				disabled: __props.disabled,
				min: __props.min,
				max: __props.max,
				step: __props.step
			}, null, 12, _hoisted_1)), [[
				vModelText,
				model.value,
				void 0,
				{ number: true }
			]]);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppSlider.js.map