import { B as useModel, K as withDirectives, M as openBlock, _ as createElementBlock, et as unref, nt as normalizeStyle, o as vModelText, w as mergeModels } from "./vue.js";
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
			default: 1
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
				style: normalizeStyle({ "--slider-position": (__props.max > __props.min ? Math.max(0, Math.min(100, (model.value - __props.min) / (__props.max - __props.min) * 100)) : 0) + "%" }),
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